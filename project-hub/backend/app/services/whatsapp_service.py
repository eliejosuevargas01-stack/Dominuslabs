"""
WhatsApp Service — Arquitetura M2M (IDPW + Whats API)

Comunicação HTTPS/TLS através da infraestrutura configurada.
A segurança de transporte TLS é responsabilidade do proxy/gateway.

Fluxo de envio:
1. Dominus identifica o usuário (`user_id`) e o tenant dele (`tenant_id`).
2. Verifica permissão interna no Dominus (`can_manage_crm` / `messages.send`).
3. Requisita ao Identity Provider (IDPW) um JWT com `tenant_id` e escopo `whatsapp:messages:send`.
4. Transmite a requisição para a Whats API com o cabeçalho `Authorization: Bearer <JWT>`.
5. A Whats API valida JWT + Tenant Lock + executa a ação.
"""
import logging
from typing import Optional
import httpx
from cachetools import TTLCache
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
from app.services.identity_service import get_m2m_jwt, invalidate_m2m_token

logger = logging.getLogger("whatsapp")

_legacy_token_cache: TTLCache = TTLCache(maxsize=256, ttl=600)


def resolve_owned_whatsapp_session(user: User, session_id: Optional[str], db: Session) -> str:
    """
    Valida positivamente se a sessão WhatsApp pertence ao tenant do usuário autenticado.
    Rejeita com 403 se pertencer a outro tenant e com 404 se a sessão for desconhecida.
    Não permite bypass global de admin em rotas tenant-scoped.
    """
    user_tenant = user.tenant_id
    if not user_tenant:
        logger.warning(f"[WA-OWNERSHIP] Usuário id={user.id} sem tenant_id ao tentar acessar sessão '{session_id}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: usuário não possui tenant_id configurado."
        )

    target_session = session_id or user.preferred_session_id
    if not target_session or target_session == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma sessão WhatsApp foi selecionada/configurada."
        )

    # 1. Prova positiva via WhatsappAccount vinculado ao banco
    account = db.query(WhatsappAccount).filter(
        WhatsappAccount.idpw == target_session
    ).first()
    if account:
        if account.tenant_id != user_tenant:
            logger.warning(
                f"[WA-OWNERSHIP] Tentativa de acesso cross-tenant! Conta '{target_session}' pertence ao tenant '{account.tenant_id}', "
                f"mas foi solicitada pelo tenant '{user_tenant}' (user={user.email}). Bloqueando antes da Whats API."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: a sessão informada pertence a outro tenant."
            )
        return target_session

    # 2. Prova positiva via preferência de usuário do mesmo tenant
    session_user = db.query(User).filter(
        User.preferred_session_id == target_session
    ).first()
    if session_user:
        if session_user.tenant_id != user_tenant:
            logger.warning(
                f"[WA-OWNERSHIP] Tentativa de acesso cross-tenant! Sessão '{target_session}' pertence ao tenant '{session_user.tenant_id}', "
                f"mas foi solicitada pelo tenant '{user_tenant}' (user={user.email}). Bloqueando antes da Whats API."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: a sessão informada pertence a outro tenant."
            )
        return target_session

    # 3. Nenhuma prova de vínculo positivo encontrada no tenant -> Rejeitar como desconhecida (fail-closed)
    logger.warning(
        f"[WA-OWNERSHIP] Sessão '{target_session}' desconhecida para o tenant '{user_tenant}' (user={user.email})."
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Sessão '{target_session}' não encontrada para o seu tenant."
    )


async def get_tenant_id_for_user(user: User, db: Session) -> str:
    """
    Retorna o tenant_id associado ao usuário.
    Se o usuário for admin, retorna ADMIN_TENANT_ID se configurado.
    Usuário comum sem tenant falha fechado (403). Nunca provisiona em runtime.
    """
    if (user.role == "admin" or user.email == settings.ADMIN_USERNAME) and settings.ADMIN_TENANT_ID:
        return settings.ADMIN_TENANT_ID
    if user.tenant_id:
        return user.tenant_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado: usuário não possui tenant_id configurado."
    )


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


async def get_oauth_token(user: User, db: Session, scope: str = "whatsapp:sessions:read") -> str:
    """
    Obtém o JWT M2M do Identity Provider (IDPW) para o tenant do usuário.
    """
    tenant_id = await get_tenant_id_for_user(user, db)
    return await get_m2m_jwt(tenant_id=tenant_id, scope=scope)


def invalidate_token(user_id: int) -> None:
    """Remove o token do cache."""
    _legacy_token_cache.pop(user_id, None)
    logger.info(f"[WA-M2M] Cache invalidado para user_id={user_id}")


async def send_whatsapp_message(
    user: User,
    db: Session,
    to_phone: str,
    message_text: str,
    session_id: str | None = None
) -> dict:
    """
    Executa o envio DIRETO de mensagem WhatsApp via Whats API utilizando IDPW + JWT.
    Comunicação HTTPS/TLS através da infraestrutura configurada.
    """
    tenant_id = await get_tenant_id_for_user(user, db)
    scope = "whatsapp:messages:send"
    jwt_token = await get_m2m_jwt(tenant_id=tenant_id, scope=scope)

    target_session = resolve_owned_whatsapp_session(user, session_id, db)

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
        f"[WA-M2M] Enviando mensagem DIRETA para Whats API. "
        f"Tenant: {tenant_id}, Sessão: {target_session}, Destinatário: {to_phone}"
    )

    return await make_whatsapp_api_request(
        "POST",
        clean_path,
        headers=headers,
        json_data=payload,
        timeout=15.0
    )

