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
from app.services.whatsapp_service import get_oauth_token, invalidate_token, check_token_validity

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

@router.get("/conversations/{lead_id}", response_model=List[Message])
async def read_conversation_messages(lead_id: str, current_user: str = Depends(get_current_user)):
    """
    Get all messages for a specific lead's conversation history.
    """
    messages = await n8n_service.get_messages(lead_id)
    return messages

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
async def send_whatsapp_message(
    payload: MessageSendPayload,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission),
):
    """
    Envia mensagem WhatsApp para o lead.
    - Resolve a sessão: usa payload.session_id ou preferred_session_id do usuário.
    - Obtém token temporário via OAuth (com cache TTL).
    - Repassa { phone, message, session_id, whatsapp_token } ao n8n.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    # Resolve sessão: payload > preferência salva
    session_id = payload.session_id or user.preferred_session_id
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma sessão WhatsApp selecionada. Escolha uma sessão ou defina uma preferência em Conexões."
        )

    try:
        # Fase 2: obtém token temporário (OAuth com cache)
        whatsapp_token = await get_oauth_token(user, db)
        
        # Verifica se o token é válido antes de enviar para o n8n
        if not await check_token_validity(whatsapp_token):
            print(f"[M2M-AUTH-FLOW] >>> Token retornado do cache/db é inválido. Forçando novo OAuth antes do envio para o n8n...", flush=True)
            invalidate_token(user.id)
            whatsapp_token = await get_oauth_token(user, db)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        data = payload.model_dump()
        data["updated_by"] = current_user
        data["session_id"] = session_id
        data["whatsapp_token"] = whatsapp_token

        message = await n8n_service.send_whatsapp_message(data)
        return message
    except ValueError as e:
        # Se for erro de autenticação detectado no n8n, tenta renovar o token e re-enviar
        if str(e) == "AUTH_ERROR_N8N_BAD_REQUEST":
            print(f"[M2M-AUTH-FLOW] >>> Detectado erro de autenticação n8n (ERR_BAD_REQUEST). Forçando novo OAuth e retentando...", flush=True)
            invalidate_token(user.id)
            try:
                new_token = await get_oauth_token(user, db)
                data["whatsapp_token"] = new_token
                print(f"[M2M-AUTH-FLOW] >>> Novo token obtido com sucesso. Re-enviando mensagem...", flush=True)
                message = await n8n_service.send_whatsapp_message(data)
                return message
            except Exception as retry_err:
                print(f"[M2M-AUTH-FLOW] >>> ❌ Falha na retentativa de envio após renovação: {retry_err}", flush=True)
                raise HTTPException(status_code=400, detail=f"Erro de autenticação na retentativa: {str(retry_err)}")
        
        # Se token inválido (outro erro de validação), invalida cache e lança HTTP 400
        invalidate_token(user.id)
        raise HTTPException(status_code=400, detail=str(e))

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
