from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.crm import Lead, LeadUpdate, Message, MessageSendPayload, CrmDashboardMetrics
from app.services.n8n_service import n8n_service, MOCK_CONVERSATIONS
from app.core.auth import get_current_user, check_crm_permission
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.whatsapp_service import send_whatsapp_message, get_oauth_token, invalidate_token, check_token_validity

router = APIRouter()

@router.get("/leads", response_model=List[Lead])
async def read_leads(current_user: str = Depends(get_current_user)):
    """
    Fetch all leads from the CRM system (routes to N8N webhook or fallback).
    """
    leads = await n8n_service.get_leads()
    return leads

@router.get("/leads/{lead_id}", response_model=Lead)
async def read_lead(lead_id: str, current_user: str = Depends(get_current_user)):
    """
    Fetch a single lead by its ID.
    """
    leads = await n8n_service.get_leads()
    lead = next((l for l in leads if str(l.get("id")) == str(lead_id)), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.put("/leads/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, lead_in: LeadUpdate, current_user: str = Depends(check_crm_permission)):
    """
    Update a lead's profile details.
    """
    result = await n8n_service.update_lead(lead_id, lead_in.model_dump(), current_user=current_user)
    return result

@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: str = Depends(check_crm_permission)):
    """
    Delete a lead.
    """
    result = await n8n_service.delete_lead(lead_id)
    return result

CONTACTS_CACHE: dict = {}

@router.get("/contacts")
async def get_contacts_action(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Action 1: 'get_contacts'
    Retorna todos os contatos agrupados por session_id para o tenant do usuário e salva no cache local.
    """
    from app.api.endpoints.whatsapp import make_whatsapp_api_request, get_user_token
    try:
        token = await get_user_token(current_user, db)
        sessions = await make_whatsapp_api_request("GET", "/api/sessions", headers={"x-session-token": token})
        if not isinstance(sessions, list):
            sessions = sessions.get("sessions", []) if isinstance(sessions, dict) else []

        result = []
        for s in sessions:
            session_id = s.get("id") or s.get("sessionId")
            if not session_id:
                continue

            try:
                contacts_res = await make_whatsapp_api_request("GET", f"/api/sessions/{session_id}/contacts", headers={"x-session-token": token})
                session_contacts = contacts_res.get("contacts", []) if isinstance(contacts_res, dict) else []
            except Exception:
                session_contacts = []

            for c in session_contacts:
                c_jid = c.get("contact_jid")
                if c_jid:
                    cache_key = f"{session_id}:{c_jid}"
                    CONTACTS_CACHE[cache_key] = c

            result.append({
                "session_id": session_id,
                "contacts": session_contacts
            })

        return result
    except Exception as e:
        print(f"[CRM-ACTION] Erro em get_contacts: {e}", flush=True)
        return []

@router.get("/conversations")
async def get_conversations_action(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Action 2: 'get_conversations'
    Retorna as últimas conversas (preview da inbox) agrupadas por session_id e complementadas com os contatos do cache.
    """
    from app.api.endpoints.whatsapp import make_whatsapp_api_request, get_user_token
    try:
        token = await get_user_token(current_user, db)
        sessions = await make_whatsapp_api_request("GET", "/api/sessions", headers={"x-session-token": token})
        if not isinstance(sessions, list):
            sessions = sessions.get("sessions", []) if isinstance(sessions, dict) else []

        result = []
        for s in sessions:
            session_id = s.get("id") or s.get("sessionId")
            if not session_id:
                continue

            try:
                convos_res = await make_whatsapp_api_request("GET", f"/api/sessions/{session_id}/conversations", headers={"x-session-token": token})
                raw_convos = convos_res.get("conversations", []) if isinstance(convos_res, dict) else []
            except Exception:
                raw_convos = []

            formatted_convos = []
            for c in raw_convos:
                c_jid = c.get("jid") or c.get("contact_jid")
                if not c_jid:
                    continue

                cache_key = f"{session_id}:{c_jid}"
                contact_info = CONTACTS_CACHE.get(cache_key, {})

                last_ts_sec = c.get("lastMessageTimestamp") or c.get("lastMessageAt") or int(datetime.utcnow().timestamp())
                if last_ts_sec > 1e11:
                    last_ts_sec = int(last_ts_sec / 1000)
                last_ts_iso = datetime.utcfromtimestamp(Number(last_ts_sec) if 'Number' in globals() else float(last_ts_sec)).isoformat() + "Z"

                formatted_convos.append({
                    "contact_jid": c_jid,
                    "session_id": session_id,
                    "unread_count": c.get("unreadCount", 0),
                    "last_message_preview": c.get("preview", ""),
                    "last_message_timestamp": last_ts_iso,
                    "created_at": last_ts_iso,
                    "updated_at": last_ts_iso,
                    "push_name": contact_info.get("push_name") or c.get("title"),
                    "display_phone": contact_info.get("display_phone") or c.get("displayJid"),
                    "profile_pic_url": contact_info.get("profile_pic_url") or c.get("imgUrl")
                })

            result.append({
                "session_id": session_id,
                "conversations": formatted_convos
            })

        return result
    except Exception as e:
        print(f"[CRM-ACTION] Erro em get_conversations: {e}", flush=True)
        return []

@router.get("/chat-history")
@router.get("/conversations/{contact_jid:path}/messages")
async def get_chat_history_action(
    contact_jid: Optional[str] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Action 3: 'get_chat_history'
    Carrega todas as mensagens de uma conversa específica agrupadas por contact_jid e session_id.
    """
    from app.api.endpoints.whatsapp import make_whatsapp_api_request, get_user_token
    target_jid = contact_jid
    if not target_jid:
        raise HTTPException(status_code=400, detail="O parâmetro 'contact_jid' é obrigatório.")

    try:
        token = await get_user_token(current_user, db)

        if not session_id:
            sessions = await make_whatsapp_api_request("GET", "/api/sessions", headers={"x-session-token": token})
            if not isinstance(sessions, list):
                sessions = sessions.get("sessions", []) if isinstance(sessions, dict) else []
            active_sessions = [s.get("id") for s in sessions if s.get("id") or s.get("sessionId")]
            session_id = active_sessions[0] if active_sessions else "default"

        msgs_res = await make_whatsapp_api_request("GET", f"/api/sessions/{session_id}/conversations/{target_jid}/messages", headers={"x-session-token": token})
        raw_msgs = msgs_res.get("messages", []) if isinstance(msgs_res, dict) else []

        formatted_messages = []
        for m in raw_msgs:
            ts_sec = m.get("timestamp") or m.get("lastMessageTimestamp") or int(datetime.utcnow().timestamp())
            if ts_sec > 1e11:
                ts_sec = int(ts_sec / 1000)
            ts_iso = datetime.utcfromtimestamp(float(ts_sec)).isoformat() + "Z"

            formatted_messages.append({
                "message_id": m.get("id") or f"msg_{ts_sec}",
                "contact_jid": target_jid,
                "session_id": session_id,
                "is_from_me": bool(m.get("fromMe")),
                "chat_kind": m.get("kind") or ("group" if "g.us" in target_jid else "private"),
                "message_type": m.get("type") or "conversation",
                "content": m.get("text") or m.get("body") or "",
                "status": m.get("status") or "received",
                "message_timestamp": ts_iso,
                "created_at": ts_iso
            })

        return [
            {
                "contact_jid": target_jid,
                "session_id": session_id,
                "messages": formatted_messages
            }
        ]
    except Exception as e:
        print(f"[CRM-ACTION] Erro em get_chat_history: {e}", flush=True)
        return [
            {
                "contact_jid": target_jid,
                "session_id": session_id or "default",
                "messages": []
            }
        ]

@router.get("/progressive/{contact_jid}")
async def get_progressive_assembled_profile(contact_jid: str, current_user: str = Depends(get_current_user)):
    """
    Retorna o perfil completo montado progressivamente no cache pelo contact_jid.
    """
    from app.services.n8n_service import ProgressiveContactCache
    profile = ProgressiveContactCache.get_assembled_payload(contact_jid)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado no cache")
    return profile

# ---------------------------------------------------------------------------
# Preferência de sessão WhatsApp
# ---------------------------------------------------------------------------

class SessionPreferencePayload(BaseModel):
    session_id: str

@router.get("/preferences/session")
async def get_session_preference(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Retorna a sessão WhatsApp preferida do usuário para envio de mensagens."""
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return {"session_id": user.preferred_session_id}

@router.put("/preferences/session")
async def set_session_preference(
    payload: SessionPreferencePayload,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission),
):
    """Define a sessão WhatsApp preferida do usuário para envio de mensagens."""
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    user.preferred_session_id = payload.session_id
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
    Envia mensagem WhatsApp DIRETAMENTE para a WhatsApp API via mTLS + JWT (Sem n8n).
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

    to_phone = payload.phone or payload.jid
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
        default_id = res.get("message", {}).get("id") or f"msg_{int(datetime.utcnow().timestamp())}"
        default_ts = datetime.utcnow().isoformat() + "Z"

        return Message(
            id=default_id,
            sender="user",
            message=payload.message,
            channel="whatsapp",
            timestamp=default_ts
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar mensagem: {e}")

@router.get("/dashboard", response_model=CrmDashboardMetrics)
async def get_dashboard_metrics(current_user: str = Depends(get_current_user)):
    """
    Dynamically calculate CRM dashboard KPIs based on the leads list and messages.
    """
    leads = await n8n_service.get_leads()
    total_leads = len(leads)
    
    leads_novos = sum(1 for l in leads if l.get("status") == "Prospectado")
    conversas_iniciadas = sum(1 for l in leads if l.get("mensagem_enviada") is True or l.get("status") == "Abordagem Enviada")
    propostas_enviadas = sum(1 for l in leads if l.get("status") == "Diagnóstico/Proposta")
    negociacoes = sum(1 for l in leads if l.get("status") == "Negociando/Objeção")
    clientes_fechados = sum(1 for l in leads if l.get("status") == "Fechado (Win)")
    
    # Calculate sent/received from our conversations
    mensagens_enviadas = sum(sum(1 for m in msgs if m.get("sender") == "user") for msgs in MOCK_CONVERSATIONS.values())
    mensagens_recebidas = sum(sum(1 for m in msgs if m.get("sender") == "lead") for msgs in MOCK_CONVERSATIONS.values())
    
    # Count pending responses
    respostas_pendentes = 0
    for lead in leads:
        l_id = lead.get("id")
        if lead.get("status") == "RESPONDED":
            respostas_pendentes += 1
        elif l_id in MOCK_CONVERSATIONS and MOCK_CONVERSATIONS[l_id]:
            if MOCK_CONVERSATIONS[l_id][-1].get("sender") == "lead":
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
    event_type: str
    metadata: Optional[Dict[str, Any]] = None

@router.get("/leads/{lead_id}/activities")
async def get_lead_activities(lead_id: str, current_user: str = Depends(get_current_user)):
    """
    Get the timeline history of activities/events for a lead.
    """
    return await n8n_service.get_activities(lead_id)

@router.post("/leads/{lead_id}/activities")
async def log_lead_activity(lead_id: str, payload: ActivityCreatePayload, current_user: str = Depends(check_crm_permission)):
    """
    Create a new activity log entry for a lead (e.g. proposal_opened).
    """
    return await n8n_service.create_activity(lead_id, payload.event_type, payload.metadata or {})
