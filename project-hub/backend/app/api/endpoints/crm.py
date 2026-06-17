from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.schemas.crm import Lead, LeadUpdate, Message, MessageSendPayload, CrmDashboardMetrics
from app.services.n8n_service import n8n_service, MOCK_CONVERSATIONS
from app.core.auth import get_current_user, check_crm_permission
from datetime import datetime

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

@router.post("/messages/send", response_model=Message)
async def send_whatsapp_message(payload: MessageSendPayload, current_user: str = Depends(check_crm_permission)):
    """
    Send an outbound WhatsApp message to the lead.
    """
    try:
        message = await n8n_service.send_whatsapp_message(payload.model_dump())
        return message
    except ValueError as e:
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
