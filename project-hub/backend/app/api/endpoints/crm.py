"""
Documentação do módulo crm.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para crm.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para crm funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.schemas.crm import Lead, LeadUpdate, Message, MessageSendPayload, CrmDashboardMetrics
from app.services.n8n_service import (
    MOCK_CONVERSATIONS,
    ProgressiveContactCache,
)
from app.core.auth import get_current_user, check_crm_permission
from app.services.crm_db import get_leads as db_get_leads, update_lead as db_update_lead, delete_lead as db_delete_lead, get_activities as db_get_activities, create_activity as db_create_activity
from app.services.crm_service import get_contacts as db_get_contacts
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.whatsapp_service import send_whatsapp_message

router = APIRouter()


def resolve_current_user_tenant(db: Session, current_user: str) -> tuple[User, str]:
    """
    Resolve o usuário autenticado e seu tenant_id em modo estritamente fail-closed.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado: usuário não possui tenant_id configurado.")
    return user, tenant_id


@router.get("/leads", response_model=List[Lead])
async def read_leads(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Fetch all contacts from the database directly, without n8n dependency.
    Returns contacts from the 'contacts' table (saved by dominus_resposta_lead flow).
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    
    # Query contacts table directly (saved by dominus_resposta_lead)
    from sqlalchemy import text as sa_text
    q = """
        SELECT
            contact_jid,
            push_name,
            display_phone,
            profile_pic_url,
            created_at,
            updated_at,
            tenant_id
        FROM contacts
        WHERE tenant_id = :tenant_id
        ORDER BY updated_at DESC
    """
    rows = db.execute(sa_text(q), {"tenant_id": tenant_id}).fetchall()
    
    mapped = []
    for row in rows:
        c = dict(row._mapping)
        # Convert datetime to string if needed
        created_at = c.get("created_at")
        updated_at = c.get("updated_at")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        if hasattr(updated_at, "isoformat"):
            updated_at = updated_at.isoformat()
        
        d = {
            "id": c.get("contact_jid") or "",
            "tenant_id": c.get("tenant_id") or tenant_id,
            "push_name": c.get("push_name") or "Contato Sem Nome",
            "nome": c.get("push_name") or "Contato Sem Nome",
            "company_name": c.get("push_name") or "Contato Sem Nome",
            "empresa_nome": c.get("push_name") or "Contato Sem Nome",
            "display_phone": c.get("display_phone") or "",
            "whatsapp": c.get("display_phone") or "",
            "session_id": "default",
            "whatsapp_instance": "default",
            "contact_jid": c.get("contact_jid") or "",
            "profile_pic_url": c.get("profile_pic_url") or "",
            "instagram": "",
            "email": "",
            "email_contato": "",
            "status": "Em Atendimento",
            "origin": "WhatsApp",
            "has_messages": True,
            "notes": "",
            "proposal": "",
            "responsible": "Eliezer",
            "last_interaction": str(updated_at) if updated_at else "",
            "created_at": str(created_at) if created_at else "",
            "falha_identificada": "",
            "segmento": "",
            "solucao_recomendada": "",
            "mensagem_enviada": True,
            "ultima_mensagem": "",
            "payload": {}
        }
        mapped.append(d)
    return mapped


@router.get("/leads/{lead_id}", response_model=Lead)
async def read_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch a single lead by its ID.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    leads = db_get_leads(db, tenant_id=tenant_id)
    lead = next((l for l in leads if str(l.get("lead_id")) == str(lead_id)), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Map database lead to CRM schema format
    d = {
        "id": lead.get("lead_id") or lead.get("id") or "",
        "tenant_id": lead.get("tenant_id") or tenant_id,
        "push_name": lead.get("empresa_nome") or lead.get("nome") or "Contato Sem Nome",
        "nome": lead.get("empresa_nome") or lead.get("nome") or "Contato Sem Nome",
        "company_name": lead.get("empresa_nome") or lead.get("nome") or "Contato Sem Nome",
        "empresa_nome": lead.get("empresa_nome") or lead.get("nome") or "Contato Sem Nome",
        "display_phone": lead.get("telefone_contato") or lead.get("whatsapp") or "",
        "whatsapp": lead.get("telefone_contato") or lead.get("whatsapp") or "",
        "session_id": lead.get("session_id") or "default",
        "whatsapp_instance": lead.get("session_id") or "default",
        "contact_jid": lead.get("contact_jid") or lead.get("jid") or "",
        "profile_pic_url": lead.get("profile_pic_url") or "",
        "instagram": lead.get("instagram") or "",
        "email": lead.get("email_contato") or lead.get("email") or "",
        "email_contato": lead.get("email_contato") or lead.get("email") or "",
        "status": lead.get("status") or "Prospectado",
        "origin": lead.get("origem") or "Instagram",
        "has_messages": False,
        "notes": lead.get("notes") or "",
        "proposal": lead.get("proposta_inicial") or "",
        "responsible": lead.get("responsible") or "Eliezer",
        "last_interaction": lead.get("updated_at") or lead.get("data_coleta") or "",
        "created_at": lead.get("created_at") or lead.get("data_coleta") or "",
        "falha_identificada": lead.get("falha_identificada") or "",
        "segmento": lead.get("nicho") or "",
        "solucao_recomendada": lead.get("solucao_recomendada") or "",
        "mensagem_enviada": False,
        "ultima_mensagem": "",
        "payload": {}
    }
    return d


@router.put("/leads/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: str,
    lead_in: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Update a lead's profile details.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    updated = db_update_lead(db, lead_id=lead_id, tenant_id=tenant_id, data=lead_in.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Map database lead to CRM schema format
    d = {
        "id": updated.get("lead_id") or updated.get("id") or "",
        "tenant_id": updated.get("tenant_id") or tenant_id,
        "push_name": updated.get("empresa_nome") or updated.get("nome") or "Contato Sem Nome",
        "nome": updated.get("empresa_nome") or updated.get("nome") or "Contato Sem Nome",
        "company_name": updated.get("empresa_nome") or updated.get("nome") or "Contato Sem Nome",
        "empresa_nome": updated.get("empresa_nome") or updated.get("nome") or "Contato Sem Nome",
        "display_phone": updated.get("telefone_contato") or updated.get("whatsapp") or "",
        "whatsapp": updated.get("telefone_contato") or updated.get("whatsapp") or "",
        "session_id": updated.get("session_id") or "default",
        "whatsapp_instance": updated.get("session_id") or "default",
        "contact_jid": updated.get("contact_jid") or updated.get("jid") or "",
        "profile_pic_url": updated.get("profile_pic_url") or "",
        "instagram": updated.get("instagram") or "",
        "email": updated.get("email_contato") or updated.get("email") or "",
        "email_contato": updated.get("email_contato") or updated.get("email") or "",
        "status": updated.get("status") or "Prospectado",
        "origin": updated.get("origem") or "Instagram",
        "has_messages": False,
        "notes": updated.get("notes") or "",
        "proposal": updated.get("proposta_inicial") or "",
        "responsible": updated.get("responsible") or "Eliezer",
        "last_interaction": updated.get("updated_at") or updated.get("data_coleta") or "",
        "created_at": updated.get("created_at") or updated.get("data_coleta") or "",
        "falha_identificada": updated.get("falha_identificada") or "",
        "segmento": updated.get("nicho") or "",
        "solucao_recomendada": updated.get("solucao_recomendada") or "",
        "mensagem_enviada": False,
        "ultima_mensagem": "",
        "payload": {}
    }
    return d


@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Delete a lead.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    deleted = db_delete_lead(db, lead_id=lead_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "id": lead_id}


# ---------------------------------------------------------------------------
# Omnichannel Actions (get_contacts, get_conversations, get_chat_history)
# ---------------------------------------------------------------------------


@router.get("/contacts")
async def get_contacts_action(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Action 1: get_contacts
    Retorna a lista completa de contatos cadastrados.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    contacts = await db_get_contacts(db, tenant_id=tenant_id)
    return contacts


@router.get("/conversations")
async def get_conversations_action(
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Retorna prévia de todas as conversas do tenant, direto do banco.
    JOIN com contacts para push_name, display_phone, profile_pic_url.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    from sqlalchemy import text as sa_text

    q = """
        SELECT
            conv.contact_jid,
            conv.session_id,
            conv.unread_count,
            conv.last_message_preview,
            conv.last_message_timestamp,
            conv.participant_pushname,
            conv.participant,
            conv.tenant_id,
            conv.updated_at,
            c.push_name,
            c.display_phone,
            c.profile_pic_url
        FROM conversations conv
        LEFT JOIN contacts c ON c.contact_jid = conv.contact_jid AND c.tenant_id = conv.tenant_id
        WHERE conv.tenant_id = :tenant_id
        {session_filter}
        ORDER BY conv.last_message_timestamp DESC NULLS LAST
        LIMIT 300
    """.format(
        session_filter="AND conv.session_id = :session_id" if session_id else ""
    )

    params: dict = {"tenant_id": tenant_id}
    if session_id:
        params["session_id"] = session_id

    rows = db.execute(sa_text(q), params).fetchall()

    result = []
    for row in rows:
        ts = row.last_message_timestamp
        ts_iso = ts.isoformat() if ts else ""
        result.append({
            "contact_jid":              row.contact_jid,
            "session_id":               row.session_id,
            "push_name":                row.push_name or row.participant_pushname or row.contact_jid,
            "display_phone":            row.display_phone,
            "profile_pic_url":          row.profile_pic_url or "",
            "unread_count":             row.unread_count or 0,
            "last_message_preview":     row.last_message_preview or "",
            "last_message_timestamp":   ts_iso,
            "participant_pushname":     row.participant_pushname,
            "participant":              row.participant,
            "tenant_id":                row.tenant_id,
        })
    return result


@router.patch("/conversations/read")
async def mark_conversation_as_read(
    payload: "MarkConversationReadPayload",
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Marca uma conversa como lida (unread_count=0).
    
    Endpoint PATCH /api/v1/crm/conversations/read
    
    Body: { "jid": string, "session_id": optional_string }
    Action: UPDATE conversations SET unread_count=0, updated_at=now() WHERE jid=body.jid AND tenant_id='admin'
    Return: { "ok": true }
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    
    from sqlalchemy import text as sa_text
    
    q = """
        UPDATE conversations
        SET unread_count = 0,
            updated_at = now()
        WHERE contact_jid = :jid
          AND tenant_id = :tenant_id
    """
    
    params = {"jid": payload.jid, "tenant_id": tenant_id}
    
    if payload.session_id:
        q += " AND session_id = :session_id"
        params["session_id"] = payload.session_id
    
    try:
        db.execute(sa_text(q), params)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        print(f"[CRM] mark_conversation_as_read error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Falha ao marcar conversa como lida: {str(e)}")


@router.get("/chat-history/{contact_jid}")
@router.get("/conversations/{contact_jid}")
async def get_chat_history_action(
    contact_jid: str,
    session_id: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Retorna histórico de mensagens de um contato, direto do banco.
    Ordenado cronologicamente ASC (mais antigas primeiro).
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    from sqlalchemy import text as sa_text

    q = """
        SELECT
            m.message_id,
            m.contact_jid,
            m.session_id,
            m.is_from_me,
            m.chat_kind,
            m.message_type,
            m.content,
            m.status,
            m.message_timestamp,
            m.created_at,
            m.media_url,
            m.participant,
            m.participant_pushname,
            m.quoted_message_id,
            m.quoted_participant,
            m.quoted_text,
            m.reaction_text,
            m.reaction_target_message_id,
            m.reaction_target_sender_jid,
            m.tenant_id
        FROM messages m
        WHERE m.tenant_id = :tenant_id
          AND m.contact_jid = :contact_jid
          {session_filter}
        ORDER BY m.message_timestamp ASC
        LIMIT :lim
    """.format(
        session_filter="AND m.session_id = :session_id" if session_id and session_id != "default" else ""
    )

    params: dict = {"tenant_id": tenant_id, "contact_jid": contact_jid, "lim": min(limit, 1000)}
    if session_id and session_id != "default":
        params["session_id"] = session_id

    rows = db.execute(sa_text(q), params).fetchall()

    result = []
    for m in rows:
        ts = m.message_timestamp
        ts_iso = ts.isoformat() if ts else ""
        ca = m.created_at
        ca_iso = ca.isoformat() if ca else ""
        from_me = bool(m.is_from_me)
        result.append({
            "message_id":                   m.message_id,
            "id":                           m.message_id,
            "contact_jid":                  m.contact_jid,
            "session_id":                   m.session_id,
            "is_from_me":                   from_me,
            "sender":                       "user" if from_me else "lead",
            "direction":                    "outgoing" if from_me else "incoming",
            "chat_kind":                    m.chat_kind or "private",
            "message_type":                 m.message_type or "conversation",
            "content":                      m.content or "",
            "message":                      m.content or "",
            "status":                       m.status or "received",
            "message_timestamp":            ts_iso,
            "timestamp":                    ts_iso,
            "created_at":                   ca_iso,
            "media_url":                    m.media_url,
            "participant":                  m.participant,
            "participant_pushname":         m.participant_pushname,
            "quoted_message_id":            m.quoted_message_id,
            "quoted_participant":           m.quoted_participant,
            "quoted_text":                  m.quoted_text,
            "reaction_text":                m.reaction_text,
            "reaction_target_message_id":   m.reaction_target_message_id,
            "reaction_target_sender_jid":   m.reaction_target_sender_jid,
            "tenant_id":                    m.tenant_id,
        })
    return result


from fastapi.responses import RedirectResponse, Response

@router.get("/avatar")
async def proxy_crm_avatar(
    request: Request,
    jid: str,
    session: Optional[str] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Proxy de avatar autenticado consumido pelo Dominus CRM via WhatsAppClient.
    Exige autenticação de usuário Dominus e resolução estrita de ownership.
    """
    target_session = (session or session_id or "").strip()
    if not jid:
        raise HTTPException(status_code=400, detail="Parâmetro 'jid' é obrigatório.")

    auth_header = request.headers.get("Authorization", "")
    effective_token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None
    if not effective_token:
        raise HTTPException(status_code=401, detail="Token de autenticação obrigatório.")

    from app.core.auth import decode_access_token
    from app.models.user import User
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    from app.services.whatsapp_client import whatsapp_client

    payload = decode_access_token(effective_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado.")

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, target_session, db)

    try:
        res = await whatsapp_client.get_session_avatar(
            tenant_id=user.tenant_id,
            session_id=resolved_session,
            jid=jid
        )
        if isinstance(res, dict):
            if res.get("_is_binary") and res.get("content"):
                return Response(
                    content=res["content"],
                    media_type=res.get("content_type") or "image/jpeg",
                    headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "private, max-age=86400", "Vary": "Authorization"}
                )
            url_target = res.get("url") or res.get("avatar_url") or res.get("profile_pic_url") or res.get("profile_url") or res.get("avatar")
            if url_target and str(url_target).startswith("http"):
                return RedirectResponse(
                    url_target,
                    status_code=302,
                    headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "private, max-age=86400", "Vary": "Authorization"}
                )
    except Exception as e:
        print(f"[CRM-AVATAR] Aviso ao buscar avatar proxy para jid={jid}: {e}", flush=True)

    raise HTTPException(status_code=404, detail="Avatar não encontrado.")


@router.get("/media")
@router.get("/sessions/{session_id}/media")
async def proxy_crm_media(
    request: Request,
    messageId: Optional[str] = None,
    message_id: Optional[str] = None,
    session: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """
    Proxy de mídia autenticado pelo Dominus via WhatsAppClient.
    Exige autenticação de usuário Dominus e resolução estrita de ownership.
    
    IMPORTANTE: Este endpoint NÃO usa Depends(get_db) para evitar manter conexão de banco
    durante todo o streaming de mídia (que pode durar segundos/minutos).
    A conexão é aberta, usada para autenticação/lookup, e fechada ANTES do streaming começar.
    """
    target_session = (session or session_id or "").strip()
    target_msg_id = messageId or message_id
    if not target_msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

    auth_header = request.headers.get("Authorization", "")
    effective_token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None
    if not effective_token:
        raise HTTPException(status_code=401, detail="Token de autenticação obrigatório.")

    from app.core.auth import decode_access_token
    from app.models.user import User
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    from app.services.whatsapp_client import whatsapp_client

    payload = decode_access_token(effective_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado.")

    # Usar context manager explícito para fechar conexão ANTES do streaming
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == payload["sub"]).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado.")

        resolved_session = resolve_owned_whatsapp_session(user, target_session, db)
        tenant_id = user.tenant_id  # Capturar antes de fechar
    finally:
        db.close()  # CRÍTICO: Liberar conexão ANTES do streaming começar

    response = await whatsapp_client.get_session_media(
        tenant_id=tenant_id,
        session_id=resolved_session,
        message_id=target_msg_id
    )

    content_type = response.headers.get("content-type", "application/octet-stream")

    async def media_stream():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()

    return StreamingResponse(
        content=media_stream(),
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "private, max-age=86400",
            "Vary": "Authorization"
        }
    )



@router.get("/progressive/{contact_jid}")
def get_progressive_assembled_profile(
    contact_jid: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Retorna o perfil completo montado progressivamente no cache pelo contact_jid isolado por tenant_id.
    """
    from app.services.n8n_service import ProgressiveContactCache
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    profile = ProgressiveContactCache.get_assembled_payload(contact_jid, tenant_id=tenant_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado no cache")
    return profile


# ---------------------------------------------------------------------------
# Preferência de sessão WhatsApp
# ---------------------------------------------------------------------------


class SessionPreferencePayload(BaseModel):
    """
    Classe SessionPreferencePayload.
    O que faz: Representa a estrutura de dados e operações para a entidade SessionPreferencePayload em o endpoint de API para crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade SessionPreferencePayload, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    session_id: str


@router.get("/preferences/session")
def get_session_preference(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Retorna a sessão WhatsApp preferida do usuário para envio de mensagens."""
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return {"session_id": user.preferred_session_id}


@router.put("/preferences/session")
@router.put("/session-preference")
def set_session_preference(
    payload: SessionPreferencePayload,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission),
):
    """Define a sessão WhatsApp preferida do usuário após validar ownership positivo."""
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    clean_session = (payload.session_id or "").strip()
    if not clean_session or clean_session.lower() == "default":
        raise HTTPException(status_code=400, detail="Sessão inválida.")

    from app.models.whatsapp_account import WhatsappAccount
    variants = {
        clean_session,
        clean_session.replace("-", " "),
        clean_session.replace(" ", "-"),
        clean_session.lower(),
        clean_session.lower().replace("-", " "),
        clean_session.lower().replace(" ", "-")
    }
    account = db.query(WhatsappAccount).filter(
        WhatsappAccount.tenant_id == user.tenant_id,
        WhatsappAccount.session_id.in_(variants)
    ).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail=f"Sessão '{payload.session_id}' não encontrada ou não pertence ao tenant '{user.tenant_id}'."
        )

    user.preferred_session_id = account.session_id
    db.commit()
    return {"session_id": user.preferred_session_id, "ok": True}


# ---------------------------------------------------------------------------
# Envio de mensagem com OAuth token
# ---------------------------------------------------------------------------


@router.post("/messages/send", response_model=Message)
async def send_crm_whatsapp_message(
    payload: MessageSendPayload,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission),
):
    """
    Envia mensagem WhatsApp DIRETAMENTE para a WhatsApp API via HTTPS/TLS com JWT (Sem n8n).
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    session_id = payload.session_id or user.preferred_session_id
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma sessão WhatsApp selecionada. Escolha uma sessão em Conexões."
        )

    to_phone = getattr(payload, "contact_jid", None) or getattr(payload, "jid", None) or getattr(payload, "lead_id", None) or payload.phone
    if not to_phone:
        raise HTTPException(
            status_code=400,
            detail="Telefone/JID do destinatário é obrigatório."
        )
    try:
        res = await send_whatsapp_message(
            user=user,
            db=db,
            to_phone=to_phone,
            message_text=payload.message,
            session_id=session_id
        )
        default_id = res.get("message", {}).get("id") or f"msg_{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}"
        default_ts = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"

        return Message(
            id=default_id,
            sender="user",
            message=payload.message,
            channel="whatsapp",
            timestamp=default_ts
        )
    except HTTPException as he:
        raise he


class MediaInputPayload(BaseModel):
    """
    Classe MediaInputPayload.
    O que faz: Representa a estrutura de dados e operações para a entidade MediaInputPayload em o endpoint de API para crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade MediaInputPayload, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    kind: str  # "image" | "video" | "audio" | "document"
    mimeType: Optional[str] = None
    fileName: Optional[str] = None
    data: str  # Base64 Data URL (data:mime;base64,...)


class MessageSendMediaPayload(BaseModel):
    """
    Classe MessageSendMediaPayload.
    O que faz: Representa a estrutura de dados e operações para a entidade MessageSendMediaPayload em o endpoint de API para crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade MessageSendMediaPayload, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    contact_jid: str
    session_id: Optional[str] = None
    text: Optional[str] = None
    caption: Optional[str] = None
    media: MediaInputPayload


@router.post("/messages/send-media")
async def send_crm_whatsapp_media(
    payload: MessageSendMediaPayload,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission),
):
    """
    Recebe payload de mídia com Base64 (data:mime;base64,...) e transmite para a WhatsApp API
    no formato padronizado POST /api/sessions/{sessionId}/messages/send com objeto 'media'.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)

    active_session = payload.session_id or user.preferred_session_id
    if not active_session:
        raise HTTPException(status_code=400, detail="Nenhuma sessão WhatsApp selecionada.")

    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    from app.services.whatsapp_client import whatsapp_client

    resolved_session = resolve_owned_whatsapp_session(user, active_session, db)

    target_jid = payload.contact_jid
    media_text = payload.text or payload.caption or ""

    wa_payload = {
        "jid": target_jid,
        "number": target_jid,
        "text": media_text,
        "media": {
            "kind": payload.media.kind,
            "mimeType": payload.media.mimeType or ("image/jpeg" if payload.media.kind == "image" else "audio/ogg; codecs=opus" if payload.media.kind == "audio" else "video/mp4" if payload.media.kind == "video" else "application/pdf"),
            "fileName": payload.media.fileName or f"file_{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}",
            "data": payload.media.data
        }
    }

    try:
        res = await whatsapp_client.send_message(
            tenant_id=tenant_id,
            session_id=resolved_session,
            message_data=wa_payload
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Falha de comunicação com WhatsApp API ao enviar mídia: {str(e)}"
        )

    from app.api.endpoints.webhooks import notify_lead_listeners, notify_crm_chat_listeners
    await notify_lead_listeners(target_jid, tenant_id=tenant_id, event="reload")
    await notify_crm_chat_listeners(target_jid, is_from_me=True, sender="user", tenant_id=tenant_id)

    return {
        "status": "success",
        "session_id": resolved_session,
        "whatsapp_response": res
    }


@router.get("/dashboard", response_model=CrmDashboardMetrics)
async def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Dynamically calculate CRM dashboard KPIs based on the leads list and messages for the user's tenant.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    leads = db_get_leads(db, tenant_id=tenant_id)
    total_leads = len(leads)
    
    leads_novos = sum(1 for l in leads if l.get("status") == "Prospectado")
    conversas_iniciadas = sum(1 for l in leads if l.get("mensagem_enviada") is True or l.get("status") == "Abordagem Enviada")
    propostas_enviadas = sum(1 for l in leads if l.get("status") == "Diagnóstico/Proposta")
    negociacoes = sum(1 for l in leads if l.get("status") == "Negociando/Objeção")
    clientes_fechados = sum(1 for l in leads if l.get("status") == "Fechado (Win)")
    
    # Calculate sent/received from our conversations scoped strictly by tenant
    tenant_msgs_list = [
        msgs for k, msgs in MOCK_CONVERSATIONS.items()
        if k.startswith(f"{tenant_id}:")
    ]
    mensagens_enviadas = sum(sum(1 for m in msgs if m.get("sender") == "user") for msgs in tenant_msgs_list)
    mensagens_recebidas = sum(sum(1 for m in msgs if m.get("sender") == "lead") for msgs in tenant_msgs_list)
    
    # Count pending responses
    respostas_pendentes = 0
    for lead in leads:
        l_id = lead.get("id")
        cache_k = f"{tenant_id}:{l_id}"
        conv = MOCK_CONVERSATIONS.get(cache_k)
        if lead.get("status") == "RESPONDED":
            respostas_pendentes += 1
        elif conv:
            if conv[-1].get("sender") == "lead":
                respostas_pendentes += 1
                
    taxa_conversao = round((clientes_fechados / total_leads * 100), 1) if total_leads > 0 else 0.0
    
    return CrmDashboardMetrics(
        total_leads=total_leads,
        leads_novos=leads_novos,
        conversas_iniciadas=conversas_iniciadas,
        mensagens_enviadas=mensagens_enviadas,
        mensagens_recebidas=mensagens_recebidas,
        respostas_pendentes=respostas_pendentes,
        propostas_enviadas=propostas_enviadas,
        negociacoes=negociacoes,
        clientes_fechados=clientes_fechados,
        taxa_conversao=taxa_conversao
    )


class MarkConversationReadPayload(BaseModel):
    """
    Classe MarkConversationReadPayload.
    O que faz: Representa a estrutura de dados para marcar uma conversa como lida.
    Impacto na regra de negócio: Atualiza unread_count=0 no banco de dados quando o usuário abre uma conversa.
    """
    jid: str
    session_id: Optional[str] = None


class ActivityCreatePayload(BaseModel):
    """
    Classe ActivityCreatePayload.
    """
    event_type: str
    metadata: Optional[Dict[str, Any]] = None


@router.get("/leads/{lead_id}/activities")
async def get_lead_activities(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get the timeline history of activities/events for a lead.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    return db_get_activities(db, lead_id=lead_id, tenant_id=tenant_id)


@router.post("/leads/{lead_id}/activities")
async def log_lead_activity(
    lead_id: str,
    payload: ActivityCreatePayload,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Create a new activity log entry for a lead (e.g. proposal_opened).
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    return db_create_activity(db, lead_id=lead_id, event_type=payload.event_type, metadata=payload.metadata or {}, tenant_id=tenant_id)
