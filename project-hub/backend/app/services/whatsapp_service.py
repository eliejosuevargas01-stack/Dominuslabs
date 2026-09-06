"""
WhatsApp Service — Arquitetura M2M (IDPW + WhatsAppClient)

Responsabilidade:
1. Autentica usuários e resolve tenant (`tenant_id`).
2. Valida ownership estrito da sessão WhatsApp (`user.tenant_id == whatsapp_account.tenant_id`).
   Nenhum fallback: admin, default, null.
3. Delega todo o envio e comunicação para o WhatsAppClient interno.
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
from app.services.identity_client import identity_client
from app.services.whatsapp_client import whatsapp_client

logger = logging.getLogger("whatsapp_service")


def resolve_owned_whatsapp_session(user: User, session_id: Optional[str], db: Session) -> str:
    """
    Valida positivamente se a sessão WhatsApp pertence ao tenant do usuário autenticado.
    user.tenant_id == whatsapp_account.tenant_id
    Rejeita com 403 se pertencer a outro tenant e com 404 se a sessão for desconhecida.
    Nenhum fallback para admin, default ou null.
    """
    user_tenant = user.tenant_id
    if not user_tenant:
        logger.warning(f"[WA-OWNERSHIP] Usuário id={user.id} sem tenant_id ao tentar acessar sessão '{session_id}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: usuário não possui tenant_id configurado."
        )

    target_session = (session_id or user.preferred_session_id or "").strip()
    if not target_session or target_session.lower() == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma sessão WhatsApp válida selecionada."
        )

    # Variantes normalizadas (hífen, espaço, lowercase) para cobrir discrepâncias de digitação/slug
    clean_target = target_session
    variants = {
        clean_target,
        clean_target.replace("-", " "),
        clean_target.replace(" ", "-"),
        clean_target.lower(),
        clean_target.lower().replace("-", " "),
        clean_target.lower().replace(" ", "-")
    }

    # 1. Prova positiva estrita via WhatsappAccount vinculado ao banco para o tenant
    accounts = db.query(WhatsappAccount).filter(
        WhatsappAccount.session_id.in_(variants)
    ).all()
    if accounts:
        for account in accounts:
            if account.tenant_id != user_tenant:
                logger.warning(
                    f"[WA-OWNERSHIP] Tentativa de acesso cross-tenant! Conta '{account.session_id}' pertence ao tenant '{account.tenant_id}', "
                    f"mas foi solicitada pelo tenant '{user_tenant}' (user={user.email}). Bloqueando antes da Whats API."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado: a sessão informada pertence a outro tenant."
                )
        matching = next((a.session_id for a in accounts if a.tenant_id == user_tenant and a.session_id == target_session), None)
        return matching or accounts[0].session_id

    # 2. Nenhuma prova de vínculo positivo em WhatsappAccount encontrada no tenant -> Rejeitar como desconhecida (fail-closed)
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
    Usuário sem tenant falha fechado (403). Sem bypass global.
    """
    if user.tenant_id:
        return user.tenant_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado: usuário não possui tenant_id configurado."
    )


async def get_oauth_token(user: User, db: Session, scope: str = "whatsapp:sessions:read") -> str:
    """
    Obtém o JWT M2M do Identity Provider (IDPW) para o tenant do usuário via IdentityClient.
    """
    tenant_id = await get_tenant_id_for_user(user, db)
    return await identity_client.get_token(tenant_id=tenant_id, scope=scope, aud="whatsapp-api")


async def check_token_validity(token: str) -> bool:
    """
    Verifica se o token M2M/JWT é válido.
    """
    return identity_client.is_token_still_valid(token)


def invalidate_token(user_id: int) -> None:
    """Função legada para compatibilidade de chamadas."""
    logger.info(f"[WA-SERVICE] invalidate_token chamado para user_id={user_id}")



async def send_whatsapp_message(
    user: User,
    db: Session,
    to_phone: str,
    message_text: str,
    session_id: Optional[str] = None
) -> dict:
    """
    Executa o envio de mensagem WhatsApp via WhatsAppClient interno.
    Escopo estrito: whatsapp:messages:send
    """
    tenant_id = await get_tenant_id_for_user(user, db)
    target_session = resolve_owned_whatsapp_session(user, session_id, db)

    cleaned_phone = "".join(filter(str.isdigit, str(to_phone)))
    final_jid = to_phone if "@" in str(to_phone) else f"{cleaned_phone}@s.whatsapp.net"

    payload = {
        "number": cleaned_phone,
        "phone": cleaned_phone,
        "message": message_text,
        "text": message_text,
        "jid": final_jid
    }

    logger.info(
        f"[WA-SERVICE] Enviando mensagem via WhatsAppClient. "
        f"Tenant: {tenant_id}, Sessão: {target_session}, Destinatário: {to_phone}"
    )

    return await whatsapp_client.send_message(
        tenant_id=tenant_id,
        session_id=target_session,
        message_data=payload
    )
