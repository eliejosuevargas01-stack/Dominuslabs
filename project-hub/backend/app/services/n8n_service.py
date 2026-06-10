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

def map_n8n_lead(lead: dict) -> dict:
    # Get ID as string
    lead_id = str(lead.get("id", lead.get("_id", "")))
    
    # Map Portuguese/Custom keys to Pydantic Lead Schema
    company_name = lead.get("nome_empresa") or lead.get("company_name") or "Empresa Sem Nome"
    
    whatsapp = lead.get("telefone") or lead.get("whatsapp") or ""
    if whatsapp == "null" or whatsapp is None:
        whatsapp = ""
        
    instagram = lead.get("instagram") or ""
    if instagram == "null" or instagram is None:
        instagram = ""
        
    email = lead.get("email") or ""
    if email == "null" or email is None:
        email = ""
        
    # Map status to uppercase standard if possible
    status_raw = str(lead.get("status", "DISCOVERED")).upper()
    if status_raw == "CONTATADO":
        status = "RESPONDED"
    elif status_raw == "NOVO":
        status = "DISCOVERED"
    else:
        status = status_raw
        
    # Infer contact method / origin
    origin_raw = lead.get("origem") or lead.get("origin") or lead.get("plataforma_veiculada") or ""
    origin_lower = str(origin_raw).lower()
    
    if "whatsapp" in origin_lower or "telefone" in origin_lower:
        origin = "WhatsApp"
    elif "instagram" in origin_lower:
        origin = "Instagram"
    elif "email" in origin_lower:
        origin = "E-mail"
    elif "facebook" in origin_lower:
        origin = "Facebook"
    elif "maps" in origin_lower or "google" in origin_lower:
        origin = "Google Maps"
    else:
        # Fallback to inferring from populated fields
        if instagram and instagram != "null":
            origin = "Instagram"
        elif whatsapp and whatsapp != "null":
            origin = "WhatsApp"
        elif email and email != "null":
            origin = "E-mail"
        else:
            origin = "Outro"
            
    # Determine if there are messages
    has_messages = False
    if lead_id in MOCK_CONVERSATIONS and len(MOCK_CONVERSATIONS[lead_id]) > 0:
        has_messages = True
    elif lead.get("has_messages") is True or lead.get("has_messages") == "true":
        has_messages = True
    
    # Map notes
    notes = lead.get("notes") or lead.get("falha_identificada") or lead.get("dor_identificada") or ""
    
    # Map proposal
    proposal = lead.get("proposta_pronta") or lead.get("proposal") or ""
    
    # Responsible
    responsible = lead.get("responsible") or lead.get("responsavel") or "Eliezer"
    
    # Dates
    last_interaction = lead.get("last_interaction") or lead.get("updatedAt") or lead.get("created_at")
    created_at = lead.get("created_at") or lead.get("createdAt")
    
    return {
        "id": lead_id,
        "company_name": company_name,
        "whatsapp": whatsapp,
        "instagram": instagram,
        "email": email,
        "status": status,
        "origin": origin,
        "has_messages": has_messages,
        "notes": notes,
        "proposal": proposal,
        "responsible": responsible,
        "last_interaction": last_interaction,
        "created_at": created_at
    }

def clean_n8n_response(res_data: Any) -> Any:
    if isinstance(res_data, list):
        if len(res_data) > 0:
            return res_data[0]
        return {}
    return res_data

class N8NService:
    @staticmethod
    async def run_scrapper(payload: dict) -> dict:
        url = settings.SCRAPPER_WEBHOOK_URL
        if not url:
            logger.info("SCRAPPER_WEBHOOK_URL not configured. Returning mock success.")
            return {"status": "success", "message": "Scrapper triggered (MOCK Mode)", "data": payload}
        
        # Map frontend platforms keys to N8N's expected target_platforms field name
        outgoing_payload = {
            "queries": payload.get("queries", []),
            "min_results": payload.get("min_results", 1000),
            "max_results": payload.get("max_results", 2000),
            "target_platforms": payload.get("platforms", [])
        }
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(url, json=outgoing_payload, timeout=30.0)
                response.raise_for_status()
                return clean_n8n_response(response.json())
            except Exception as e:
                logger.error(f"Error calling Scrapper webhook: {e}")
                return {"status": "error", "message": str(e)}

    @staticmethod
    async def get_leads() -> List[dict]:
        url = settings.CRM_GET_LEADS_WEBHOOK_URL
        if not url:
            logger.info("CRM_GET_LEADS_WEBHOOK_URL not configured. Returning mock leads.")
            mapped_mock = [map_n8n_lead(l) for l in MOCK_LEADS]
            # stable sort: last_interaction descending, then has_messages descending
            mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
            mapped_mock.sort(key=lambda x: x.get("has_messages", False), reverse=True)
            return mapped_mock
        
        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=get_leads"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(endpoint_url, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                raw_leads = []
                if isinstance(data, list):
                    raw_leads = data
                elif isinstance(data, dict) and "leads" in data:
                    raw_leads = data["leads"]
                else:
                    mapped_mock = [map_n8n_lead(l) for l in MOCK_LEADS]
                    mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
                    mapped_mock.sort(key=lambda x: x.get("has_messages", False), reverse=True)
                    return mapped_mock
                
                # Apply mapper and perform stable sorting
                mapped_leads = [map_n8n_lead(l) for l in raw_leads if isinstance(l, dict)]
                mapped_leads.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
                mapped_leads.sort(key=lambda x: x.get("has_messages", False), reverse=True)
                return mapped_leads
            except Exception as e:
                logger.error(f"Error calling GET leads webhook: {e}. Falling back to mock data.")
                mapped_mock = [map_n8n_lead(l) for l in MOCK_LEADS]
                mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
                mapped_mock.sort(key=lambda x: x.get("has_messages", False), reverse=True)
                return mapped_mock

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

        # Map outgoing fields to both English and Portuguese keys to be safe with N8N
        outgoing_payload = {**payload}
        if "company_name" in payload:
            outgoing_payload["nome_empresa"] = payload["company_name"]
        if "whatsapp" in payload:
            outgoing_payload["telefone"] = payload["whatsapp"]
        if "proposal" in payload:
            outgoing_payload["proposta_pronta"] = payload["proposal"]
        if "origin" in payload:
            outgoing_payload["origem"] = payload["origin"]

        if not url:
            logger.info("CRM_UPDATE_LEAD_WEBHOOK_URL not configured. Lead updated locally in-memory.")
            updated_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
            return updated_lead or {"id": lead_id, **payload}
            
        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=update_lead&id={lead_id}"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.put(endpoint_url, json=outgoing_payload, timeout=30.0)
                response.raise_for_status()
                res_data = clean_n8n_response(response.json())
                if isinstance(res_data, dict) and ("company_name" in res_data or "nome_empresa" in res_data):
                    return map_n8n_lead(res_data)
                return next((l for l in MOCK_LEADS if l["id"] == lead_id), {"id": lead_id, **payload})
            except Exception as e:
                logger.error(f"Error calling UPDATE lead webhook: {e}")
                return next((l for l in MOCK_LEADS if l["id"] == lead_id), {"id": lead_id, **payload})

    @staticmethod
    async def get_messages(lead_id: str) -> List[dict]:
        url = settings.CRM_GET_MESSAGES_WEBHOOK_URL
        if not url:
            logger.info(f"CRM_GET_MESSAGES_WEBHOOK_URL not configured. Returning mock messages for {lead_id}.")
            return MOCK_CONVERSATIONS.get(lead_id, [])
            
        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=get_messages&lead_id={lead_id}"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
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
        phone = payload.get("phone", "")
        
        # Clean phone number to digits-only for standard whatsapp api gateways
        cleaned_phone = "".join(c for c in phone if c.isdigit())
        
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
            
        # Match Evolution API payload structure as well as direct params
        outgoing_payload = {
            "number": cleaned_phone,
            "body": message_text,
            "phone": phone,
            "message": message_text,
            "lead_id": lead_id
        }
            
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(url, json=outgoing_payload, timeout=30.0)
                response.raise_for_status()
                try:
                    res_json = clean_n8n_response(response.json())
                    if isinstance(res_json, dict) and "message" in res_json:
                        return res_json
                except Exception:
                    pass
                return new_msg
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
            
        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=create_activity&lead_id={lead_id}"
            
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(endpoint_url, json=new_activity, timeout=30.0)
                response.raise_for_status()
                res_data = clean_n8n_response(response.json())
                if isinstance(res_data, dict) and "event_type" in res_data:
                    return res_data
                return new_activity
            except Exception as e:
                logger.error(f"Error calling CREATE activity webhook: {e}")
                return new_activity

    @staticmethod
    async def get_activities(lead_id: str) -> List[dict]:
        return MOCK_ACTIVITIES.get(lead_id, [])

n8n_service = N8NService()
