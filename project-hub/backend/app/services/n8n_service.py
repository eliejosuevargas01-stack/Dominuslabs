import httpx
import logging
from typing import List, Dict, Any
from app.core.config import settings
from datetime import datetime

logger = logging.getLogger("n8n_service")

# Stateful mock database for in-memory development fallback
MOCK_LEADS = [
    {
        "id": "lead_1",
        "company_name": "Clínica Sorriso",
        "instagram": "https://instagram.com/clinicasorriso",
        "whatsapp": "+5511999999991",
        "email": "contato@clinicasorriso.com.br",
        "status": "DISCOVERED",
        "origin": "Google Maps",
        "notes": "Pesquisar se possuem site próprio.",
        "proposal": "Desenvolvimento de Landing Page de agendamento por R$ 1.200,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T10:00:00Z",
        "created_at": "2026-06-09T08:30:00Z"
    },
    {
        "id": "lead_2",
        "company_name": "Advocacia Silva & Associados",
        "instagram": "https://instagram.com/silva_associados",
        "whatsapp": "+5511999999992",
        "email": "silva@associados.com.br",
        "status": "NEGOTIATING",
        "origin": "Instagram",
        "notes": "Cliente interessado em automação de contratos.",
        "proposal": "Funil completo + CRM Dominus por R$ 3.500,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T14:30:00Z",
        "created_at": "2026-06-08T09:15:00Z"
    },
    {
        "id": "lead_3",
        "company_name": "SolarTech Energia",
        "instagram": "https://instagram.com/solartech_energia",
        "whatsapp": "+5511999999993",
        "email": "comercial@solartech.com.br",
        "status": "CLOSED_WON",
        "origin": "Meta Ads Library",
        "notes": "Contrato assinado. Enviar onboarding.",
        "proposal": "Site institucional e SEO por R$ 5.000,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-09T18:00:00Z",
        "created_at": "2026-06-05T11:00:00Z"
    },
    {
        "id": "lead_4",
        "company_name": "Hamburgueria do Bairro",
        "instagram": "https://instagram.com/burguer_bairro",
        "whatsapp": "+5511999999994",
        "email": "burguer@bairro.com",
        "status": "RESPONDED",
        "origin": "Facebook",
        "notes": "Perguntou se integramos com cardápio online.",
        "proposal": "Cardápio inteligente + LP de captura por R$ 2.000,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T16:15:00Z",
        "created_at": "2026-06-09T15:20:00Z"
    },
    {
        "id": "lead_5",
        "company_name": "Academia VIP Fit",
        "instagram": "https://instagram.com/vipfit_academia",
        "whatsapp": "+5511999999995",
        "email": "gerencia@vipfit.com.br",
        "status": "OBJECTION",
        "origin": "Google Maps",
        "notes": "Acha o preço de R$ 3.000 alto. Negociar desconto.",
        "proposal": "Landing page de vendas por R$ 3.000,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T11:00:00Z",
        "created_at": "2026-06-07T14:40:00Z"
    }
]

MOCK_CONVERSATIONS = {
    "lead_1": [
        {"id": "m1", "sender": "lead", "message": "Olá! Gostaria de saber mais sobre os serviços de vocês.", "channel": "instagram", "timestamp": "2026-06-10T09:50:00Z"},
        {"id": "m2", "sender": "user", "message": "Olá, tudo bem? Podemos agendar uma chamada para apresentar?", "channel": "instagram", "timestamp": "2026-06-10T10:00:00Z"}
    ],
    "lead_2": [
        {"id": "m3", "sender": "lead", "message": "Vocês integram com o sistema de processos judiciais?", "channel": "whatsapp", "timestamp": "2026-06-10T14:00:00Z"},
        {"id": "m4", "sender": "user", "message": "Sim, integramos via API com a maioria dos tribunais e sistemas comerciais.", "channel": "whatsapp", "timestamp": "2026-06-10T14:30:00Z"}
    ],
    "lead_3": [
        {"id": "m5", "sender": "user", "message": "Parabéns pela parceria! O contrato já está assinado.", "channel": "whatsapp", "timestamp": "2026-06-09T17:45:00Z"},
        {"id": "m6", "sender": "lead", "message": "Obrigado! Ansioso para iniciar os trabalhos.", "channel": "whatsapp", "timestamp": "2026-06-09T18:00:00Z"}
    ],
    "lead_4": [
        {"id": "m7", "sender": "lead", "message": "Vocês trabalham com tráfego pago também?", "channel": "instagram", "timestamp": "2026-06-10T16:00:00Z"},
        {"id": "m8", "sender": "user", "message": "Sim, fazemos gestão de anúncios para Google e Meta.", "channel": "instagram", "timestamp": "2026-06-10T16:15:00Z"}
    ],
    "lead_5": [
        {"id": "m9", "sender": "user", "message": "O que achou da nossa proposta comercial?", "channel": "whatsapp", "timestamp": "2026-06-10T10:45:00Z"},
        {"id": "m10", "sender": "lead", "message": "Achei excelente, mas no momento o valor de R$ 3.000 está fora do orçamento.", "channel": "whatsapp", "timestamp": "2026-06-10T11:00:00Z"}
    ]
}

MOCK_ACTIVITIES = {
    "lead_1": [
        {"lead_id": "lead_1", "event_type": "lead_created", "timestamp": "2026-06-09T08:30:00Z", "metadata": {"origin": "Google Maps"}},
        {"lead_id": "lead_1", "event_type": "message_received", "timestamp": "2026-06-10T09:50:00Z", "metadata": {"message": "Olá! Gostaria de saber mais..."}}
    ],
    "lead_2": [
        {"lead_id": "lead_2", "event_type": "lead_created", "timestamp": "2026-06-08T09:15:00Z", "metadata": {"origin": "Instagram"}},
        {"lead_id": "lead_2", "event_type": "message_received", "timestamp": "2026-06-10T14:00:00Z", "metadata": {"message": "Vocês integram com o sistema..."}}
    ]
}

class N8NService:
    @staticmethod
    async def run_scrapper(payload: dict) -> dict:
        url = settings.SCRAPPER_WEBHOOK_URL
        if not url:
            logger.info("SCRAPPER_WEBHOOK_URL not configured. Returning mock success.")
            return {"status": "success", "message": "Scrapper triggered (MOCK Mode)", "data": payload}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error calling Scrapper webhook: {e}")
                return {"status": "error", "message": str(e)}

    @staticmethod
    async def get_leads() -> List[dict]:
        url = settings.CRM_GET_LEADS_WEBHOOK_URL
        if not url:
            logger.info("CRM_GET_LEADS_WEBHOOK_URL not configured. Returning mock leads.")
            return MOCK_LEADS
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                # Accept a list directly or a dict with a list key
                data = response.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "leads" in data:
                    return data["leads"]
                return MOCK_LEADS
            except Exception as e:
                logger.error(f"Error calling GET leads webhook: {e}. Falling back to mock data.")
                return MOCK_LEADS

    @staticmethod
    async def update_lead(lead_id: str, payload: dict) -> dict:
        url = settings.CRM_UPDATE_LEAD_WEBHOOK_URL
        
        # Sync the change to our mock state first so it persists in the developer's session
        for i, lead in enumerate(MOCK_LEADS):
            if lead["id"] == lead_id:
                # Merge fields
                for k, v in payload.items():
                    lead[k] = v
                lead["last_interaction"] = datetime.utcnow().isoformat() + "Z"
                MOCK_LEADS[i] = lead
                break

        if not url:
            logger.info("CRM_UPDATE_LEAD_WEBHOOK_URL not configured. Lead updated locally in-memory.")
            # Return the updated lead from mock list
            updated_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
            return updated_lead or {"id": lead_id, **payload}
            
        async with httpx.AsyncClient() as client:
            try:
                # Replace placeholder {id} if N8N expects it in URL, or send as payload parameter
                endpoint_url = url.replace("{id}", lead_id)
                response = await client.put(endpoint_url, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error calling UPDATE lead webhook: {e}")
                # Return local updated lead on failure
                return next((l for l in MOCK_LEADS if l["id"] == lead_id), {"id": lead_id, **payload})

    @staticmethod
    async def get_messages(lead_id: str) -> List[dict]:
        url = settings.CRM_GET_MESSAGES_WEBHOOK_URL
        if not url:
            logger.info(f"CRM_GET_MESSAGES_WEBHOOK_URL not configured. Returning mock messages for {lead_id}.")
            return MOCK_CONVERSATIONS.get(lead_id, [])
            
        async with httpx.AsyncClient() as client:
            try:
                endpoint_url = url.replace("{lead_id}", lead_id)
                response = await client.get(endpoint_url, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "messages" in data:
                    return data["messages"]
                return MOCK_CONVERSATIONS.get(lead_id, [])
            except Exception as e:
                logger.error(f"Error calling GET messages webhook: {e}. Returning mock.")
                return MOCK_CONVERSATIONS.get(lead_id, [])

    @staticmethod
    async def send_whatsapp_message(payload: dict) -> dict:
        url = settings.CRM_SEND_WHATSAPP_WEBHOOK_URL
        lead_id = payload.get("lead_id")
        message_text = payload.get("message")
        
        # Append message locally in mock conversations to show live updates
        new_msg = {
            "id": f"msg_{int(datetime.utcnow().timestamp())}",
            "sender": "user",
            "message": message_text,
            "channel": "whatsapp",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if lead_id not in MOCK_CONVERSATIONS:
            MOCK_CONVERSATIONS[lead_id] = []
        MOCK_CONVERSATIONS[lead_id].append(new_msg)

        # Update last interaction timestamp on lead
        for lead in MOCK_LEADS:
            if lead["id"] == lead_id:
                lead["last_interaction"] = datetime.utcnow().isoformat() + "Z"
                break

        # Log event message_sent
        new_act = {
            "lead_id": lead_id,
            "event_type": "message_sent",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"message": message_text, "channel": "whatsapp"}
        }
        if lead_id not in MOCK_ACTIVITIES:
            MOCK_ACTIVITIES[lead_id] = []
        MOCK_ACTIVITIES[lead_id].append(new_act)

        if not url:
            logger.info("CRM_SEND_WHATSAPP_WEBHOOK_URL not configured. Message logged locally in-memory.")
            return new_msg
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error calling SEND whatsapp message webhook: {e}")
                return new_msg

    @staticmethod
    async def create_activity(lead_id: str, event_type: str, metadata: dict) -> dict:
        url = settings.CRM_CREATE_ACTIVITY_WEBHOOK_URL
        new_activity = {
            "lead_id": lead_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata
        }
        if lead_id not in MOCK_ACTIVITIES:
            MOCK_ACTIVITIES[lead_id] = []
        MOCK_ACTIVITIES[lead_id].append(new_activity)

        if not url:
            logger.info("CRM_CREATE_ACTIVITY_WEBHOOK_URL not configured. Activity logged locally.")
            return new_activity
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=new_activity, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error calling CREATE activity webhook: {e}")
                return new_activity

    @staticmethod
    async def get_activities(lead_id: str) -> List[dict]:
        return MOCK_ACTIVITIES.get(lead_id, [])

n8n_service = N8NService()
