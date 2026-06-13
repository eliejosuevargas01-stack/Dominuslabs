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
        "status": "Prospectado",
        "origin": "WhatsApp",
        "notes": "Pesquisar se possuem site próprio.",
        "proposal": "Desenvolvimento de Landing Page de agendamento por R$ 1.200,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T10:00:00Z",
        "created_at": "2026-06-09T08:30:00Z",
        "falha_identificada": "Sem Landing Page",
        "segmento": "Dentista",
        "solucao_recomendada": "Landing Page",
        "id_anuncio_meta": "972540022197311",
        "facebook_page_url": "https://www.facebook.com/clinicasorriso/",
        "tem_site_proprio": False,
        "dor_identificada": "[\"formulario horrivel\"]"
    },
    {
        "id": "lead_2",
        "company_name": "Advocacia Silva & Associados",
        "instagram": "https://instagram.com/silva_associados",
        "whatsapp": "",
        "email": "silva@associados.com.br",
        "status": "Negociando/Objeção",
        "origin": "Instagram",
        "notes": "Cliente interessado em automação de contratos.",
        "proposal": "Funil completo + CRM Dominus por R$ 3.500,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T14:30:00Z",
        "created_at": "2026-06-08T09:15:00Z",
        "falha_identificada": "Sem Pixel do Facebook",
        "segmento": "Advogado",
        "solucao_recomendada": "CRM"
    },
    {
        "id": "lead_3",
        "company_name": "SolarTech Energia",
        "instagram": "",
        "whatsapp": "",
        "email": "comercial@solartech.com.br",
        "status": "Fechado (Win)",
        "origin": "E-mail",
        "notes": "Contrato assinado. Enviar onboarding.",
        "proposal": "Site institucional e SEO por R$ 5.000,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-09T18:00:00Z",
        "created_at": "2026-06-05T11:00:00Z",
        "falha_identificada": "Site lento no mobile",
        "segmento": "Energia Solar",
        "solucao_recomendada": "SEO"
    },
    {
        "id": "lead_4",
        "company_name": "Hamburgueria do Bairro",
        "instagram": "",
        "whatsapp": "+5511999999994",
        "email": "",
        "status": "Abordagem Enviada",
        "origin": "WhatsApp",
        "notes": "Perguntou se integramos com cardápio online.",
        "proposal": "Cardápio inteligente + LP de captura por R$ 2.000,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T16:15:00Z",
        "created_at": "2026-06-09T15:20:00Z",
        "falha_identificada": "Sem botão de WhatsApp",
        "segmento": "Restaurante",
        "solucao_recomendada": "Cardápio Digital"
    },
    {
        "id": "lead_5",
        "company_name": "Academia VIP Fit",
        "instagram": "",
        "whatsapp": "",
        "email": "",
        "status": "Negociando/Objeção",
        "origin": "Outro",
        "notes": "Acha o preço de R$ 3.000 alto. Negociar desconto.",
        "proposal": "Landing page de vendas por R$ 3.000,00.",
        "responsible": "Eliezer",
        "last_interaction": "2026-06-10T11:00:00Z",
        "created_at": "2026-06-07T14:40:00Z",
        "falha_identificada": "Formulário de contato quebrado",
        "segmento": "Academia",
        "solucao_recomendada": "Landing Page"
    }
]

MOCK_CONVERSATIONS = {
    "lead_1": [
        {"id": "m1", "sender": "lead", "message": "Olá! Gostaria de saber mais sobre os serviços de vocês.", "channel": "whatsapp", "timestamp": "2026-06-10T09:50:00Z"},
        {"id": "m2", "sender": "user", "message": "Olá, tudo bem? Podemos agendar uma chamada para apresentar?", "channel": "whatsapp", "timestamp": "2026-06-10T10:00:00Z"}
    ],
    "lead_2": [
        {"id": "m3", "sender": "lead", "message": "Gostaria de ver alguns portfólios no Instagram.", "channel": "instagram", "timestamp": "2026-06-10T14:00:00Z"},
        {"id": "m4", "sender": "user", "message": "Claro! Nosso perfil é @dominuslabs. Enviamos novidades por lá.", "channel": "instagram", "timestamp": "2026-06-10T14:30:00Z"}
    ],
    "lead_4": [
        {"id": "m7", "sender": "lead", "message": "Vocês trabalham com tráfego pago também?", "channel": "whatsapp", "timestamp": "2026-06-10T16:00:00Z"},
        {"id": "m8", "sender": "user", "message": "Sim, fazemos gestão de anúncios para Google e Meta.", "channel": "whatsapp", "timestamp": "2026-06-10T16:15:00Z"}
    ]
}

MOCK_ACTIVITIES = {
    "lead_1": [
        {"lead_id": "lead_1", "event_type": "lead_created", "timestamp": "2026-06-09T08:30:00Z", "metadata": {"origin": "WhatsApp"}},
        {"lead_id": "lead_1", "event_type": "message_received", "timestamp": "2026-06-10T09:50:00Z", "metadata": {"message": "Olá! Gostaria de saber mais..."}}
    ],
    "lead_2": [
        {"lead_id": "lead_2", "event_type": "lead_created", "timestamp": "2026-06-08T09:15:00Z", "metadata": {"origin": "Instagram"}},
        {"lead_id": "lead_2", "event_type": "message_received", "timestamp": "2026-06-10T14:00:00Z", "metadata": {"message": "Gostaria de ver alguns portfólios..."}}
    ]
}

def map_n8n_lead(lead: dict, conversations_map: dict = None) -> dict:
    # Get ID as string (check lead_id first for the new payload)
    lead_id = str(lead.get("id" if "id" in lead else "lead_id", lead.get("_id", "")))
    if not lead_id or lead_id.lower() == "none":
        # Fallback if lead_id was none/empty
        lead_id = str(lead.get("id", lead.get("lead_id", lead.get("_id", ""))))

    # Extract nested payload dict safely
    payload_dict = lead.get("payload") or {}
    if not isinstance(payload_dict, dict):
        payload_dict = {}

    # Map Portuguese/Custom keys to Pydantic Lead Schema
    company_name = lead.get("nome_empresa") or lead.get("empresa_nome") or lead.get("company_name") or "Empresa Sem Nome"

    # Extract and clean contact fields, handling None, "null", and whitespace
    raw_tel = lead.get("telefone") or lead.get("telefone_contato")
    raw_wa = lead.get("whatsapp")
    whatsapp = ""
    for val in (raw_tel, raw_wa):
        if val is not None and str(val).strip().lower() not in ("null", ""):
            whatsapp = str(val).strip()
            break

    raw_ig = lead.get("instagram")
    instagram = ""
    if raw_ig is not None and str(raw_ig).strip().lower() not in ("null", ""):
        instagram = str(raw_ig).strip()

    # Fallback to link_destibo_botao or url_site if instagram is empty but they contain instagram.com
    if not instagram:
        for val in (lead.get("link_destibo_botao"), lead.get("url_site"), payload_dict.get("url_site")):
            if val is not None and "instagram.com" in str(val).lower():
                instagram = str(val).strip()
                break

    raw_email = lead.get("email") or lead.get("email_contato") or payload_dict.get("email")
    email = ""
    if raw_email is not None and str(raw_email).strip().lower() not in ("null", ""):
        email = str(raw_email).strip()

    # Map status to support Portuguese custom stages
    status_raw = str(lead.get("status") or "Prospectado").strip()
    status_upper = status_raw.upper()
    if status_upper in ("NOVO", "FRIO", "DISCOVERED", "PROSPECTADO"):
        status = "Prospectado"
    elif status_upper in ("CONTATADO", "RESPONDED", "ABORDAGEM ENVIADA", "ABORDADO", "OUTREACH_SENT", "AGUARDANDO_RETORNO", "ABORDAGEM INICIADA"):
        status = "Abordagem Enviada"
    elif status_upper in ("EM QUALIFICACAO", "EM QUALIFICAÇÃO", "QUALIFIED", "INTERESTED"):
        status = "Em Qualificação"
    elif status_upper in ("DIAGNOSTICO/PROPOSTA", "DIAGNÓSTICO/PROPOSTA", "PROPOSAL_SENT"):
        status = "Diagnóstico/Proposta"
    elif status_upper in ("NEGOCIANDO/OBJECEAO", "NEGOCIANDO/OBJEÇÃO", "NEGOTIATING", "OBJECTION", "NEGOCIANDO/OBJECEÃO"):
        status = "Negociando/Objeção"
    elif status_upper in ("GANHO", "FECHADO", "CLOSED_WON", "FECHADO (WIN)", "WIN"):
        status = "Fechado (Win)"
    elif status_upper in ("PERDIDO", "CLOSED_LOST", "PERDIDO (LOSS)", "LOSS"):
        status = "Perdido (Loss)"
    else:
        status = status_raw

    # Infer contact method / origin based on populated fields priority
    origin = lead.get("origem") or lead.get("origin")
    if not origin or str(origin).strip().lower() == "null":
        if whatsapp:
            origin = "WhatsApp"
        elif instagram:
            origin = "Instagram"
        elif email:
            origin = "E-mail"
        else:
            origin = "Outro"
    
    # Capitalize origin properly if it maps to known ones
    origin_lower = str(origin).strip().lower()
    if origin_lower == "whatsapp":
        origin = "WhatsApp"
    elif origin_lower == "instagram":
        origin = "Instagram"
    elif origin_lower in ("e-mail", "email"):
        origin = "E-mail"
    elif origin_lower == "telefone":
        origin = "Telefone"
    elif origin_lower == "outro":
        origin = "Outro"

    # Determine if there are messages
    has_messages = False
    if lead_id in MOCK_CONVERSATIONS and len(MOCK_CONVERSATIONS[lead_id]) > 0:
        has_messages = True
    elif conversations_map and lead_id in conversations_map and len(conversations_map[lead_id]) > 0:
        has_messages = True
    elif lead.get("has_messages") is True or lead.get("has_messages") == "true":
        has_messages = True

    # Determine if a message was sent by the user (mensagem_enviada)
    mensagem_enviada = False
    if lead_id in MOCK_CONVERSATIONS:
        if any(m.get("sender") == "user" for m in MOCK_CONVERSATIONS[lead_id]):
            mensagem_enviada = True
    if conversations_map and lead_id in conversations_map:
        if any(
            m.get("tipo") == "mensagem_enviada" or
            m.get("sender") == "user" or
            (m.get("mensagem_enviada") is not None and str(m.get("mensagem_enviada")).strip().lower() not in ("null", ""))
            for m in conversations_map[lead_id]
        ):
            mensagem_enviada = True
    raw_me = lead.get("mensagem_enviada") or lead.get("has_sent_message")
    if raw_me is True or str(raw_me).strip().lower() == "true":
        mensagem_enviada = True

    # If the status is "Abordagem Enviada", it means a message was sent (mensagem_enviada and has_messages should be True)
    if status == "Abordagem Enviada":
        mensagem_enviada = True
        has_messages = True

    # If a message was sent but status is still Prospectado, advance to Abordagem Enviada
    if mensagem_enviada and status == "Prospectado":
        status = "Abordagem Enviada"

    # Map notes
    notes = lead.get("notes") or lead.get("falha_identificada") or lead.get("dor_identificada") or ""
    if notes is not None and str(notes).strip().lower() in ("null", ""):
        notes = ""

    # Map proposal
    proposal = lead.get("proposta_pronta") or lead.get("proposal") or lead.get("proposta_inicial") or ""
    if proposal is not None and str(proposal).strip().lower() in ("null", ""):
        proposal = ""

    # Responsible
    responsible = lead.get("responsible") or lead.get("responsavel") or "Eliezer"
    if responsible is not None and str(responsible).strip().lower() in ("null", ""):
        responsible = "Eliezer"

    # Dates
    last_interaction = lead.get("last_interaction") or lead.get("updated_at") or lead.get("updatedAt") or lead.get("created_at") or lead.get("data_coleta")
    created_at = lead.get("created_at") or lead.get("createdAt") or lead.get("data_coleta")

    if conversations_map and lead_id in conversations_map and conversations_map[lead_id]:
        # Get the latest message timestamp
        latest_msg = max(conversations_map[lead_id], key=lambda x: x.get("data") or x.get("timestamp") or x.get("createdAt") or "")
        latest_ts = latest_msg.get("data") or latest_msg.get("timestamp") or latest_msg.get("createdAt")
        if latest_ts:
            if not last_interaction or latest_ts > last_interaction:
                last_interaction = latest_ts

    # Extract and clean additional fields, handling None, "null", and whitespace
    raw_falha = lead.get("falha_identificada")
    falha_identificada = ""
    if raw_falha is not None and str(raw_falha).strip().lower() not in ("null", ""):
        falha_identificada = str(raw_falha).strip()
    elif notes:
        falha_identificada = notes

    raw_segmento = lead.get("segmento") or lead.get("nicho")
    segmento = ""
    if raw_segmento is not None and str(raw_segmento).strip().lower() not in ("null", ""):
        segmento = str(raw_segmento).strip()

    raw_solucao = lead.get("solucao_recomendada") or lead.get("servico_ofertado")
    solucao_recomendada = ""
    if raw_solucao is not None and str(raw_solucao).strip().lower() not in ("null", ""):
        solucao_recomendada = str(raw_solucao).strip()

    # Base mapped lead with all keys
    mapped_lead = {
        **lead,
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
        "created_at": created_at,
        "falha_identificada": falha_identificada,
        "segmento": segmento,
        "solucao_recomendada": solucao_recomendada,
        "mensagem_enviada": mensagem_enviada
    }

    # Reconstruct id_anuncio_meta from other potential places
    id_anuncio_meta = (
        lead.get("id_anuncio_meta")
        or lead.get("ad_archive_id")
        or payload_dict.get("id_anuncio_meta")
        or (lead.get("payload") or {}).get("id_anuncio_meta") if isinstance(lead.get("payload"), dict) else None
    )
    if id_anuncio_meta:
        mapped_lead["id_anuncio_meta"] = str(id_anuncio_meta).strip()

    # Flatten nested payload dictionary fields directly to the top-level
    for k, v in payload_dict.items():
        if k not in mapped_lead or mapped_lead[k] is None or mapped_lead[k] == "":
            mapped_lead[k] = v

    # Delete original Portuguese raw keys, metadata and raw payload to avoid duplicate display
    keys_to_remove = [
        "lead_id", "empresa_nome", "nome_empresa", "telefone_contato", "telefone",
        "email_contato", "origem", "nicho", "data_coleta", "updated_at", "updatedAt",
        "createdAt", "payload"
    ]
    for k in keys_to_remove:
        if k in mapped_lead:
            del mapped_lead[k]

    return mapped_lead

def clean_n8n_response(res_data: Any) -> Any:
    if isinstance(res_data, list):
        if len(res_data) > 0:
            return res_data[0]
        return {}
    return res_data

def map_n8n_message(msg: dict, lead_channel: str = "whatsapp") -> List[dict]:
    mapped = []
    msg_id = str(msg.get("id", ""))
    created_at = msg.get("createdAt") or msg.get("data")
    updated_at = msg.get("updatedAt") or msg.get("data")

    # 1. User message (mensagem_enviada)
    user_text = msg.get("mensagem_enviada")
    if user_text is not None and str(user_text).strip().lower() not in ("null", ""):
        mapped.append({
            "id": f"{msg_id}_user",
            "sender": "user",
            "message": str(user_text).strip(),
            "channel": lead_channel,
            "timestamp": created_at
        })
    elif msg.get("tipo") == "mensagem_enviada":
        # Fallback if text is empty but type is message sent
        mapped.append({
            "id": f"{msg_id}_user_fallback",
            "sender": "user",
            "message": "Mensagem enviada",
            "channel": lead_channel,
            "timestamp": created_at
        })

    # 2. Lead reply (resposta)
    lead_text = msg.get("resposta")
    if lead_text is not None and str(lead_text).strip().lower() not in ("null", ""):
        mapped.append({
            "id": f"{msg_id}_lead",
            "sender": "lead",
            "message": str(lead_text).strip(),
            "channel": lead_channel,
            "timestamp": updated_at
        })

    return mapped

class N8NService:
    @staticmethod
    async def run_scrapper(payload: dict, platform: str = "meta_ads") -> dict:
        fallback_url = settings.SCRAPPER_META_WEBHOOK_URL if platform == "meta_ads" else settings.SCRAPPER_MAPS_WEBHOOK_URL
        url = payload.get("webhook_url") or fallback_url
        if not url:
            logger.info("SCRAPPER Webhook URL not configured. Returning mock success.")
            return {"status": "success", "message": "Scrapper triggered (MOCK Mode)", "data": payload}

        # Map frontend platforms keys to N8N's expected target_platforms field name
        outgoing_payload = {
            "queries": payload.get("queries", []),
            "min_results": payload.get("min_results", 10),
            "max_results": payload.get("max_results", 20),
        }
        if "target_platform" in payload:
            outgoing_payload["target_platform"] = payload["target_platform"]
        if "contact_channel" in payload:
            outgoing_payload["contact_channel"] = payload["contact_channel"]
        if "objective" in payload:
            outgoing_payload["objective"] = payload["objective"]

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
            # stable sort: last_interaction descending, then mensagem_enviada descending
            mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
            mapped_mock.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
            return mapped_mock

        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=get_leads"

        raw_leads = None
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(endpoint_url, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    raw_leads = data
                elif isinstance(data, dict) and "leads" in data:
                    raw_leads = data["leads"]
            except Exception as e:
                logger.error(f"Error calling GET leads webhook: {e}. Falling back to mock data.")

        if raw_leads is None:
            mapped_mock = [map_n8n_lead(l) for l in MOCK_LEADS]
            mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
            mapped_mock.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
            return mapped_mock

        # Apply mapper and perform stable sorting
        mapped_leads = [map_n8n_lead(l) for l in raw_leads if isinstance(l, dict)]
        mapped_leads.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
        mapped_leads.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
        return mapped_leads

    @staticmethod
    async def update_lead(lead_id: str, payload: dict) -> dict:
        url = settings.CRM_UPDATE_LEAD_WEBHOOK_URL

        # Reconstruct the nested payload dictionary if any of its keys are in payload
        payload_keys = [
            "tem_cta", "url_site", "tem_formulario", "id_anuncio_meta",
            "tem_site_proprio", "erros_identificados_site"
        ]
        
        has_payload_updates = any(k in payload for k in payload_keys)
        
        # Look up existing payload dict in mock state
        existing_payload_dict = {}
        for lead in MOCK_LEADS:
            if lead.get("id") == lead_id:
                raw_p = lead.get("payload")
                if isinstance(raw_p, dict):
                    existing_payload_dict = raw_p
                break

        # Reconstruct the payload dict
        reconstructed_payload = {**existing_payload_dict}
        for k in payload_keys:
            if k in payload:
                reconstructed_payload[k] = payload[k]
        if "email" in payload:
            reconstructed_payload["email"] = payload["email"]

        # Sync the change to our mock state first so it persists in the developer's session
        for i, lead in enumerate(MOCK_LEADS):
            if lead["id"] == lead_id:
                # Merge fields
                for k, v in payload.items():
                    lead[k] = v
                
                # Ensure the nested payload is also updated inside the mock lead
                lead["payload"] = reconstructed_payload
                lead["last_interaction"] = datetime.utcnow().isoformat() + "Z"
                MOCK_LEADS[i] = lead
                break

        # Map outgoing fields to both English and Portuguese keys to be safe with N8N
        outgoing_payload = {**payload}
        if "company_name" in payload:
            outgoing_payload["nome_empresa"] = payload["company_name"]
            outgoing_payload["empresa_nome"] = payload["company_name"]
        if "whatsapp" in payload:
            outgoing_payload["telefone"] = payload["whatsapp"]
            outgoing_payload["telefone_contato"] = payload["whatsapp"]
        if "email" in payload:
            outgoing_payload["email_contato"] = payload["email"]
        if "proposal" in payload:
            outgoing_payload["proposta_pronta"] = payload["proposal"]
            outgoing_payload["proposta_inicial"] = payload["proposal"]
        if "origin" in payload:
            outgoing_payload["origem"] = payload["origin"]
        if "segmento" in payload:
            outgoing_payload["nicho"] = payload["segmento"]

        # Include the reconstructed nested payload dict in the outgoing payload
        if has_payload_updates or reconstructed_payload:
            outgoing_payload["payload"] = reconstructed_payload

        if not url:
            logger.info("CRM_UPDATE_LEAD_WEBHOOK_URL not configured. Lead updated locally in-memory.")
            updated_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
            return map_n8n_lead(updated_lead) if updated_lead else map_n8n_lead({"id": lead_id, **payload})

        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=update_lead&id={lead_id}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.put(endpoint_url, json=outgoing_payload, timeout=30.0)
                response.raise_for_status()
                res_data = clean_n8n_response(response.json())
                if isinstance(res_data, dict) and ("company_name" in res_data or "nome_empresa" in res_data or "empresa_nome" in res_data):
                    return map_n8n_lead(res_data)

                fallback_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
                if fallback_lead:
                    return map_n8n_lead(fallback_lead)
                return map_n8n_lead({"id": lead_id, **payload})
            except Exception as e:
                logger.error(f"Error calling UPDATE lead webhook: {e}")
                fallback_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
                if fallback_lead:
                    return map_n8n_lead(fallback_lead)
                return map_n8n_lead({"id": lead_id, **payload})

    @staticmethod
    async def get_messages(lead_id: str) -> List[dict]:
        all_msgs = list(MOCK_CONVERSATIONS.get(lead_id, []))
        url = settings.CRM_GET_MESSAGES_WEBHOOK_URL
        if not url:
            return all_msgs

        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=get&lead_id={lead_id}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(endpoint_url, timeout=30.0)
                response.raise_for_status()
                body = response.text.strip()
                raw_msgs = []
                if body:
                    data = response.json()
                    if isinstance(data, list):
                        raw_msgs = data
                    elif isinstance(data, dict):
                        # Support if N8N returns the lead object with its messages nested
                        raw_msgs = data.get("messages") or data.get("conversas") or data.get("historico") or data.get("history") or []
                        if not isinstance(raw_msgs, list):
                            raw_msgs = [data]

                # Fetch lead to get correct channel (origin)
                lead_channel = "whatsapp"
                try:
                    leads = await N8NService.get_leads()
                    lead_obj = next((l for l in leads if l["id"] == lead_id), None)
                    if lead_obj and lead_obj.get("origin"):
                        lead_channel = lead_obj["origin"].lower()
                except Exception:
                    pass

                # Map and flatten messages
                existing_ids = {m.get("id") for m in all_msgs if m.get("id")}
                for m in raw_msgs:
                    if isinstance(m, dict):
                        # Filter by lead_id in Python if N8N returned all conversation histories
                        m_lead_id = str(m.get("lead_id") or m.get("leadId") or "")
                        if m_lead_id and m_lead_id != str(lead_id):
                            continue
                        mapped_list = map_n8n_message(m, lead_channel)
                        for mapped_msg in mapped_list:
                            if mapped_msg.get("id") not in existing_ids:
                                all_msgs.append(mapped_msg)
                                existing_ids.add(mapped_msg.get("id"))

                all_msgs.sort(key=lambda x: x.get("timestamp") or "")
                return all_msgs
            except Exception as e:
                logger.error(f"Error calling GET messages webhook: {e}. Returning mock.")
                return all_msgs

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
        new_activity = {
            "lead_id": lead_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata
        }
        if lead_id not in MOCK_ACTIVITIES:
            MOCK_ACTIVITIES[lead_id] = []
        MOCK_ACTIVITIES[lead_id].append(new_activity)
        return new_activity

    @staticmethod
    async def get_activities(lead_id: str) -> List[dict]:
        return MOCK_ACTIVITIES.get(lead_id, [])

n8n_service = N8NService()
