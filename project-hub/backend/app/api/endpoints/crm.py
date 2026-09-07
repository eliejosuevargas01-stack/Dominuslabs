"""
Documentação do módulo crm.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para crm.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para crm funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.crm import Lead, LeadUpdate, Message, MessageSendPayload, CrmDashboardMetrics
from app.services.n8n_service import n8n_service, MOCK_CONVERSATIONS
from app.core.auth import get_current_user, check_crm_permission
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.whatsapp_service import send_whatsapp_message, get_oauth_token, invalidate_token, check_token_validity

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
    Fetch all leads from the n8n CRM webhook or fallback to direct WhatsApp API.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    try:
        leads = await n8n_service.get_leads(user_id=current_user, tenant_id=tenant_id)
        if leads and len(leads) > 0:
            return leads
    except Exception as e:
        print(f"[CRM] n8n get_leads falhou: {e}", flush=True)

    from app.services.n8n_service import map_n8n_lead
    raw_contacts = await get_contacts_action(db=db, current_user=current_user)
    return [map_n8n_lead(c, tenant_id=tenant_id) for c in raw_contacts if isinstance(c, dict)]

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
    leads = await n8n_service.get_leads(user_id=current_user, tenant_id=tenant_id)
    lead = next((l for l in leads if str(l.get("id")) == str(lead_id)), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

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
    result = await n8n_service.update_lead(lead_id, lead_in.model_dump(), current_user=current_user, tenant_id=tenant_id)
    return result

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
    result = await n8n_service.delete_lead(lead_id, user_id=current_user, tenant_id=tenant_id)
    return result

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
    try:
        leads = await n8n_service.get_leads(user_id=current_user, tenant_id=tenant_id)
        contacts = []
        for l in leads:
            contacts.append({
                "contact_jid": l.get("contact_jid") or l.get("jid") or l.get("id"),
                "push_name": l.get("push_name") or l.get("nome") or "Contato Sem Nome",
                "display_phone": l.get("display_phone") or l.get("whatsapp") or None,
                "profile_pic_url": l.get("profile_pic_url") or "",
                "created_at": l.get("created_at") or datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "updated_at": l.get("updated_at") or datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "tenant_id": tenant_id
            })
        return contacts
    except Exception as e:
        print(f"[CRM] get_contacts_action error: {e}", flush=True)
        return []

@router.get("/conversations")
async def get_conversations_action(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Action 2: get_conversations
    Retorna a prévia de todas as conversas agrupadas ou separadas por sessão.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    try:
        convs = await n8n_service.get_conversations(user_id=current_user, tenant_id=tenant_id)
        if convs and len(convs) > 0:
            return convs
    except Exception as e:
        print(f"[CRM] n8n get_conversations error: {e}", flush=True)

    # Fallback return standard leads format mapped to conversations preview
    leads = await n8n_service.get_leads(user_id=current_user, tenant_id=tenant_id)
    result = []
    for l in leads:
        result.append({
            "contact_jid": l.get("contact_jid") or l.get("jid") or l.get("id"),
            "push_name": l.get("push_name") or l.get("nome") or "Contato",
            "display_phone": l.get("display_phone") or l.get("whatsapp") or None,
            "profile_pic_url": l.get("profile_pic_url") or "",
            "session_id": l.get("session_id") or "default",
            "unread_count": l.get("unread_count", 0),
            "last_message_preview": l.get("last_message_preview") or l.get("ultima_mensagem") or "",
            "last_message_timestamp": l.get("last_message_timestamp") or l.get("last_interaction") or l.get("updated_at") or datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        })
    return result

@router.get("/chat-history/{contact_jid}")
@router.get("/conversations/{contact_jid}")
async def get_chat_history_action(
    contact_jid: str,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Action 3: get_chat_history
    Busca o histórico de mensagens de uma conversa com n8n ou Whats API.
    """
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    lookup_id = f"{contact_jid}___{session_id}" if session_id and session_id != "default" else contact_jid
    return await n8n_service.get_messages(lookup_id, user_id=current_user, tenant_id=tenant_id)

from fastapi.responses import RedirectResponse, Response

@router.get("/avatar")
async def proxy_crm_avatar(
    request: Request,
    jid: str,
    session: Optional[str] = None,
    session_id: Optional[str] = None,
    token: Optional[str] = Query(None),
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
    effective_token = token or (auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None)
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
                    headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "private, max-age=86400"}
                )
            url_target = res.get("url") or res.get("avatar_url") or res.get("profile_pic_url") or res.get("profile_url") or res.get("avatar")
            if url_target and str(url_target).startswith("http"):
                return RedirectResponse(
                    url_target,
                    status_code=302,
                    headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "private, max-age=86400"}
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
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Proxy de mídia autenticado pelo Dominus via WhatsAppClient.
    Exige autenticação de usuário Dominus e resolução estrita de ownership.
    """
    target_session = (session or session_id or "").strip()
    target_msg_id = messageId or message_id
    if not target_msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

    auth_header = request.headers.get("Authorization", "")
    effective_token = token or (auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None)
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

    response = await whatsapp_client.get_session_media(
        tenant_id=user.tenant_id,
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
            "Cache-Control": "public, max-age=86400"
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
    leads = await n8n_service.get_leads(user_id=current_user, tenant_id=tenant_id)
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

from pydantic import BaseModel
from typing import Dict, Any, Optional

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
    return await n8n_service.get_activities(lead_id, tenant_id=tenant_id)

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
    return await n8n_service.create_activity(lead_id, payload.event_type, payload.metadata or {}, tenant_id=tenant_id)
