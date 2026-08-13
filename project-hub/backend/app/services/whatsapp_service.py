"""
WhatsApp Service — Arquitetura M2M (mTLS + JWT do Identity Worker)

Fluxo final de envio:
1. Dominius identifica o usuário (`user_id`) e o tenant dele (`tenant_id`).
2. Verifica permissão interna no Dominius (`can_manage_crm` / `messages.send`).
3. Requisita ao Identity Worker via mTLS um JWT com `tenant_id` e escopo `whatsapp:messages:send`.
4. Transmite a requisição para a WhatsApp API via mTLS com o cabeçalho `Authorization: Bearer <JWT>`.
5. A WhatsApp API valida mTLS + JWT + Tenant Lock + executa a ação.
"""
import logging
import httpx
from cachetools import TTLCache
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.mtls_client import get_mtls_async_client
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
from app.services.identity_service import get_m2m_jwt, invalidate_m2m_token

logger = logging.getLogger("whatsapp")

_legacy_token_cache: TTLCache = TTLCache(maxsize=256, ttl=600)


async def get_tenant_id_for_user(user: User, db: Session) -> str:
    """
    Retorna o tenant_id associado ao usuário.
    Se o usuário for admin, retorna 'admin' para permitir acesso universal às sessões master.
    """
    if user.role == "admin" or user.email == settings.ADMIN_USERNAME:
        return settings.ADMIN_TENANT_ID

    if user.tenant_id:
        return user.tenant_id

    tenant_id = f"tenant_{user.id}"
    user.tenant_id = tenant_id
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"[WA-M2M] Atribuído tenant_id={tenant_id} para o usuário id={user.id}")
    return tenant_id


async def check_token_validity(token: str) -> bool:
    """
    Verifica se o token M2M/JWT é válido sem depender de bibliotecas externas (PyJWT).
    """
    if not token or "." not in token:
        return False
    try:
        import base64
        import json
        import time

        parts = token.split(".")
        if len(parts) != 3:
            return False

        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        exp = payload.get("exp", 0)
        return exp > time.time()
    except Exception as e:
        logger.warning(f"[WA-M2M] Token M2M/JWT inválido ou expirado: {e}")
        return False


async def get_oauth_token(user: User, db: Session, scope: str = "whatsapp:messages:send whatsapp:sessions:read whatsapp:sessions:write") -> str:
    """
    Obtém o JWT M2M do Identity Worker para o tenant do usuário.
    """
    tenant_id = await get_tenant_id_for_user(user, db)
    return await get_m2m_jwt(tenant_id=tenant_id, scope=scope)


def invalidate_token(user_id: int) -> None:
    """Remove o token do cache."""
    _legacy_token_cache.pop(user_id, None)
    logger.info(f"[WA-M2M] Cache legado invalidado para user_id={user_id}")


async def send_whatsapp_message(
    user: User,
    db: Session,
    to_phone: str,
    message_text: str,
    session_id: str | None = None
) -> dict:
    """
    Executa o envio DIRETO de mensagem WhatsApp utilizando mTLS + JWT sem n8n:
    Dominius ⇄ mTLS ⇄ Identity Worker ──(JWT)──► Dominius ⇄ mTLS ⇄ WhatsApp API
    """
    tenant_id = await get_tenant_id_for_user(user, db)
    scope = "whatsapp:messages:send"
    jwt_token = await get_m2m_jwt(tenant_id=tenant_id, scope=scope)

    target_session = session_id or user.preferred_session_id
    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sessão do WhatsApp não especificada."
        )

    from app.api.endpoints.whatsapp import make_whatsapp_api_request
    clean_path = f"/api/sessions/{target_session}/messages/send"
    payload = {
        "number": to_phone,
        "message": message_text
    }
    headers = {
        "x-session-token": jwt_token,
        "x-tenant-id": tenant_id,
        "Authorization": f"Bearer {jwt_token}"
    }

    logger.info(
        f"[WA-M2M] Enviando mensagem DIRETA via mTLS + JWT para WhatsApp API. "
        f"Tenant: {tenant_id}, Sessão: {target_session}, Destinatário: {to_phone}"
    )

    return await make_whatsapp_api_request(
        "POST",
        clean_path,
        headers=headers,
        json_data=payload,
        timeout=15.0
    )
