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
    Se o usuário ainda não tiver um tenant_id definido no banco, atribui e persiste `tenant_{user.id}`.
    """
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
    Verifica se o token M2M/JWT é válido.
    """
    if not token:
        return False
    try:
        import jwt
        # Tenta decodificar o token sem verificar a assinatura para checar expiração
        decoded = jwt.decode(token, options={"verify_signature": False})
        import time
        if decoded.get("exp", 0) > time.time():
            return True
        return False
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
    Executa o envio de mensagem WhatsApp utilizando a cadeia M2M mTLS + JWT:
    Dominius ⇄ mTLS ⇄ Identity Worker ──(JWT)──► Dominius ⇄ mTLS ⇄ WhatsApp API
    """
    # 1. Identifica o tenant do usuário
    tenant_id = await get_tenant_id_for_user(user, db)

    # 2. Requisita JWT M2M ao Identity Worker via mTLS (sem fallbacks ou bypasses)
    scope = "whatsapp:messages:send"
    jwt_token = await get_m2m_jwt(tenant_id=tenant_id, scope=scope)

    # 3. Define URL da WhatsApp API
    base_url = settings.WHATSAPP_API_URL.rstrip("/")
    url = f"{base_url}/api/messages/send"

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "x-tenant-id": tenant_id,
        "Content-Type": "application/json"
    }

    payload = {
        "to": to_phone,
        "message": message_text,
        "session_id": session_id or user.preferred_session_id
    }

    logger.info(
        f"[WA-M2M] Enviando mensagem via mTLS + JWT para WhatsApp API. "
        f"Tenant: {tenant_id}, Destinatário: {to_phone}"
    )

    try:
        async with get_mtls_async_client(timeout=15.0, service_name="whatsapp") as client:
            resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code in (200, 201):
                logger.info(f"[WA-M2M] ✅ Mensagem enviada com sucesso para {to_phone}!")
                return resp.json()
            elif resp.status_code in (401, 403):
                logger.error(f"[WA-M2M] ❌ Tenant Lock ou Permissão recusada pela WhatsApp API: {resp.text[:200]}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Acesso negado pela WhatsApp API (Tenant Lock / Scope): {resp.text[:200]}"
                )
            else:
                logger.error(f"[WA-M2M] Erro no envio WhatsApp API. Status: {resp.status_code}, Body: {resp.text[:200]}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Falha na chamada à WhatsApp API (status {resp.status_code})."
                )
    except httpx.RequestError as e:
        logger.error(f"[WA-M2M] ❌ Conexão com WhatsApp API falhou em {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço WhatsApp API inacessível em {url}."
        )
