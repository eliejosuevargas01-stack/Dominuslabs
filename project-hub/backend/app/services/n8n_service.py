import httpx
import logging
import json
import copy
import re
import time
from typing import List, Dict, Any, Optional
from app.core.config import settings
from datetime import datetime

RAW_LEADS_CACHE = {}


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

def safe_parse_json(val: Any) -> dict:
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}

def map_n8n_lead(lead: dict, conversations_map: dict = None) -> dict:
    raw_id = str(lead.get("id") or lead.get("lead_id") or lead.get("_id") or "")
    c_jid = str(lead.get("contact_jid") or lead.get("jid") or "")
    session_id = lead.get("session_id") or lead.get("whatsapp_instance") or ""

    if raw_id and "___" in raw_id:
        lead_id = raw_id
    elif c_jid and session_id and session_id != "default":
        lead_id = f"{c_jid}___{session_id}"
    elif c_jid:
        lead_id = c_jid
    elif raw_id:
        lead_id = raw_id
    else:
        lead_id = "unknown_lead"

    if lead_id and lead_id.lower() != "none" and lead_id != "":
        RAW_LEADS_CACHE[lead_id] = copy.deepcopy(lead)
        if c_jid and c_jid != lead_id and c_jid not in RAW_LEADS_CACHE:
            RAW_LEADS_CACHE[c_jid] = copy.deepcopy(lead)

    raw_payload = lead.get("payload")
    payload_dict = safe_parse_json(raw_payload) if isinstance(raw_payload, str) else (raw_payload or {})
    if not isinstance(payload_dict, dict):
        payload_dict = {}

    person_name = ""
    for name_key in ("push_name", "nome", "nome_empresa", "empresa_nome", "company_name"):
        val = lead.get(name_key)
        if val and isinstance(val, str) and val.strip() and val.strip().lower() not in ("desconhecido", "unknown", "null", "none") and "@lid" not in val.lower() and "@s.whatsapp.net" not in val.lower():
            person_name = val.strip()
            break

    if not person_name:
        raw_phone = lead.get("display_phone") or lead.get("whatsapp") or lead.get("telefone_contato") or lead.get("phone")
        if raw_phone and isinstance(raw_phone, str) and raw_phone.strip() and raw_phone.strip().lower() not in ("null", "none"):
            person_name = raw_phone.strip()

    if not person_name:
        raw_jid = lead.get("contact_jid") or lead.get("jid") or lead.get("id")
        if raw_jid and isinstance(raw_jid, str) and raw_jid.strip() and raw_jid.strip().lower() not in ("null", "none"):
            person_name = raw_jid.strip()
        else:
            person_name = "Contato Sem Nome"

    company_name = person_name

    raw_tel = lead.get("display_phone") or lead.get("telefone") or lead.get("telefone_contato")
    raw_wa = lead.get("whatsapp") or lead.get("phone")
    whatsapp = ""
    for val in (raw_tel, raw_wa):
        if val is not None and str(val).strip().lower() not in ("null", ""):
            whatsapp = str(val).strip()
            break

    raw_ig = lead.get("instagram")
    instagram = ""
    if raw_ig is not None and str(raw_ig).strip().lower() not in ("null", ""):
        instagram = str(raw_ig).strip()

    if not instagram:
        for val in (lead.get("link_destibo_botao"), lead.get("url_site"), payload_dict.get("url_site")):
            if val is not None and "instagram.com" in str(val).lower():
                instagram = str(val).strip()
                break

    raw_email = lead.get("email") or lead.get("email_contato") or payload_dict.get("email")
    email = ""
    if raw_email is not None and str(raw_email).strip().lower() not in ("null", ""):
        email = str(raw_email).strip()

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

    if whatsapp:
        origin = "WhatsApp"
    elif instagram:
        origin = "Instagram"
    elif email:
        origin = "E-mail"
    else:
        origin = "Instagram"
        # Fallback to Instagram: generate a slugified username based on the company name
        import unicodedata
        import re
        clean_name = unicodedata.normalize('NFKD', company_name).encode('ASCII', 'ignore').decode('ASCII')
        instagram = re.sub(r'[^a-zA-Z0-9_.]', '', clean_name.replace(" ", "").lower())

    has_messages = False
    if lead_id in MOCK_CONVERSATIONS and len(MOCK_CONVERSATIONS[lead_id]) > 0:
        has_messages = True
    elif conversations_map and lead_id in conversations_map and len(conversations_map[lead_id]) > 0:
        has_messages = True
    elif lead.get("has_messages") is True or lead.get("has_messages") == "true":
        has_messages = True

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

    if status == "Abordagem Enviada":
        mensagem_enviada = True
        has_messages = True

    if mensagem_enviada and status == "Prospectado":
        status = "Abordagem Enviada"

    notes = lead.get("notes") or lead.get("falha_identificada") or lead.get("dor_identificada") or ""
    if notes is not None and str(notes).strip().lower() in ("null", ""):
        notes = ""

    proposal = lead.get("proposta_pronta") or lead.get("proposal") or lead.get("proposta_inicial") or ""
    if proposal is not None and str(proposal).strip().lower() in ("null", ""):
        proposal = ""

    responsible = lead.get("responsible") or lead.get("responsavel") or "Eliezer"
    if responsible is not None and str(responsible).strip().lower() in ("null", ""):
        responsible = "Eliezer"

    last_interaction = lead.get("last_interaction") or lead.get("updated_at") or lead.get("updatedAt") or lead.get("created_at") or lead.get("data_coleta")
    created_at = lead.get("created_at") or lead.get("createdAt") or lead.get("data_coleta")

    ultima_mensagem = lead.get("ultima_mensagem") or lead.get("content") or lead.get("message") or ""
    if "mensagens" in lead and isinstance(lead["mensagens"], list) and len(lead["mensagens"]) > 0:
        has_messages = True
        for m in reversed(lead["mensagens"]):
            if isinstance(m, dict):
                m_txt = m.get("content") or m.get("message") or ""
                if m_txt:
                    ultima_mensagem = m_txt
                    ts_last = m.get("message_timestamp") or m.get("created_at")
                    if ts_last and (not last_interaction or ts_last > str(last_interaction)):
                        last_interaction = ts_last
                    break

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

    profile_pic = lead.get("profile_pic_url") or lead.get("avatar") or ""
    session_id = lead.get("session_id") or lead.get("whatsapp_instance") or ""
    if not session_id and profile_pic and "/api/sessions/" in profile_pic:
        try:
            session_id = profile_pic.split("/api/sessions/")[1].split("/")[0]
        except Exception:
            pass
    if not session_id:
        session_id = "default"

    if profile_pic and profile_pic.startswith("/"):
        profile_pic = f"https://whats.dominuslabs.online{profile_pic}"

    mapped_lead = {
        **lead,
        "id": lead_id,
        "push_name": person_name,
        "nome": person_name,
        "company_name": person_name,
        "empresa_nome": person_name,
        "display_phone": whatsapp or lead.get("display_phone") or "",
        "whatsapp": whatsapp or lead.get("display_phone") or "",
        "telefone_contato": whatsapp or lead.get("display_phone") or "",
        "session_id": session_id,
        "whatsapp_instance": session_id,
        "contact_jid": lead.get("jid") or lead.get("contact_jid") or "",
        "profile_pic_url": profile_pic,
        "instagram": instagram,
        "email": email,
        "email_contato": email,
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
        "mensagem_enviada": mensagem_enviada,
        "ultima_mensagem": ultima_mensagem or lead.get("ultima_mensagem") or "",
        "payload": payload_dict
    }

    origem_plataforma = lead.get("origem") or lead.get("origin") or ""
    if origin_lower := str(origem_plataforma).strip().lower():
        if origin_lower in ("whatsapp", "instagram", "e-mail", "email", "telefone", "outro"):
            origem_plataforma = ""
    mapped_lead["origem"] = origem_plataforma

    id_anuncio_meta = (
        lead.get("id_anuncio_meta")
        or lead.get("ad_archive_id")
        or payload_dict.get("id_anuncio_meta")
        or (lead.get("payload") or {}).get("id_anuncio_meta") if isinstance(lead.get("payload"), dict) else None
    )
    if id_anuncio_meta:
        mapped_lead["id_anuncio_meta"] = str(id_anuncio_meta).strip()

    for k, v in payload_dict.items():
        if k not in mapped_lead or mapped_lead[k] is None or mapped_lead[k] == "":
            mapped_lead[k] = v

    presenca = safe_parse_json(lead.get("presenca_digital"))
    reputacao = safe_parse_json(lead.get("reputacao_google"))
    oportunidades = safe_parse_json(lead.get("oportunidades_identificadas"))
    diagnostico = safe_parse_json(presenca.get("diagnostico_site"))

    mapped_lead["presenca_digital_url_site"] = presenca.get("url_site") or lead.get("url_site") or ""
    mapped_lead["presenca_digital_status_site"] = presenca.get("status_site") or ""
    mapped_lead["presenca_digital_tem_cta"] = diagnostico.get("tem cta") or diagnostico.get("tem_cta") or ""
    mapped_lead["presenca_digital_url_abre"] = diagnostico.get("url abre") or diagnostico.get("url_abre") or ""
    mapped_lead["presenca_digital_demora_abrir"] = diagnostico.get("demora pra abrir?") or diagnostico.get("demora_abrir") or ""
    mapped_lead["presenca_digital_formulario_captacao"] = diagnostico.get("tem formulario de captação?") or diagnostico.get("formulario_captacao") or ""
    
    mapped_lead["reputacao_google_nota_media"] = reputacao.get("nota_media")
    mapped_lead["reputacao_google_total_avaliacoes"] = reputacao.get("total_avaliacoes")

    mapped_lead["oportunidades_identificadas_telefone_fixo"] = oportunidades.get("telefone_fixo")
    mapped_lead["oportunidades_identificadas_urgencia_site"] = oportunidades.get("urgencia_de_site") or oportunidades.get("urgencia_site")
    mapped_lead["oportunidades_identificadas_urgencia_avaliacoes"] = oportunidades.get("urgencia_de_avaliacoes") or oportunidades.get("urgencia_avaliacoes")
    mapped_lead["oportunidades_identificadas_urgencia_gestao_reputacao"] = oportunidades.get("urgencia_de_gestao_reputacao") or oportunidades.get("urgencia_gestao_reputacao")

    keys_to_remove = [
        "lead_id", "empresa_nome", "nome_empresa", "telefone_contato", "telefone",
        "email_contato", "origin", "nicho", "data_coleta", "updated_at", "updatedAt",
        "createdAt", "presenca_digital", "reputacao_google", "oportunidades_identificadas"
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

def parse_embedded_timestamp(text: str) -> tuple[str, str | None]:
    """
    Searches for [DD/MM/YYYY HH:MM:SS] at the end of the text.
    Returns (cleaned_text, iso_timestamp_str).
    """
    if not text:
        return text, None
    pattern = r'\s*\[(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\]\s*$'
    match = re.search(pattern, text)
    if match:
        day, month, year, hour, minute, second = match.groups()
        cleaned_text = re.sub(pattern, '', text).strip()
        # Output format: YYYY-MM-DDTHH:MM:SS
        iso_ts = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
        return cleaned_text, iso_ts
    return text, None

def extract_text_content(m: dict) -> str:
    if not isinstance(m, dict):
        return ""

    for field in ["content", "message", "text", "body", "caption", "conversation"]:
        val = m.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip()

    for field in ["message", "content", "extendedTextMessage"]:
        val = m.get(field)
        if isinstance(val, dict):
            sub_text = extract_text_content(val)
            if sub_text:
                return sub_text

    if "extendedTextMessage" in m and isinstance(m["extendedTextMessage"], dict):
        text_val = m["extendedTextMessage"].get("text") or m["extendedTextMessage"].get("caption")
        if isinstance(text_val, str) and text_val.strip():
            return text_val.strip()

    return ""

def map_n8n_message(msg: dict, lead_channel: str = "whatsapp") -> List[dict]:
    mapped = []

    # 1. Support nested "mensagens" array format from n8n chat history payload
    if "mensagens" in msg and isinstance(msg["mensagens"], list):
        session_id = msg.get("session_id")
        contact_jid = msg.get("contact_jid")
        push_name = msg.get("push_name")
        display_phone = msg.get("display_phone")
        parent_is_from_me = msg.get("is_from_me", False)
        
        profile_pic_url = msg.get("profile_pic_url") or ""
        if profile_pic_url and profile_pic_url.startswith("/"):
            profile_pic_url = f"https://whats.dominuslabs.online{profile_pic_url}"

        for m in msg["mensagens"]:
            if not isinstance(m, dict):
                continue
            msg_id = str(m.get("message_id") or m.get("id") or "")
            is_from_me = m.get("is_from_me") if "is_from_me" in m else parent_is_from_me
            sender = "user" if is_from_me else "lead"
            direction = "outgoing" if is_from_me else "incoming"

            raw_text = extract_text_content(m)
            image_url = m.get("image_url") or m.get("media_url") or m.get("url") or m.get("file_url") or m.get("image") or ""
            if image_url and image_url.startswith("/"):
                image_url = f"https://whats.dominuslabs.online{image_url}"

            ts = m.get("message_timestamp") or m.get("created_at") or m.get("timestamp") or m.get("createdAt") or msg.get("created_at")

            mapped.append({
                "id": msg_id,
                "message_id": msg_id,
                "session_id": m.get("session_id") or session_id,
                "contact_jid": contact_jid,
                "is_from_me": is_from_me,
                "sender": sender,
                "direction": direction,
                "sent_by_user": is_from_me,
                "message": raw_text,
                "content": raw_text,
                "caption": m.get("caption", ""),
                "message_type": m.get("message_type", "conversation"),
                "chat_kind": msg.get("chat_kind", "private"),
                "image_url": image_url,
                "media_url": image_url,
                "push_name": push_name,
                "display_phone": display_phone,
                "profile_pic_url": profile_pic_url,
                "channel": lead_channel,
                "timestamp": ts,
                "status": m.get("status") or msg.get("status", "received")
            })
        return mapped

    # 2. Support direct whats-api / n8n single incoming message object
    if "is_from_me" in msg or "message_id" in msg or "contact_jid" in msg or "push_name" in msg or "session_id" in msg:
        msg_id = str(msg.get("message_id") or msg.get("id") or "")
        is_from_me = msg.get("is_from_me", False)
        sender = "user" if is_from_me else "lead"
        direction = "outgoing" if is_from_me else "incoming"
        
        raw_text = extract_text_content(msg)
        image_url = msg.get("image_url") or msg.get("media_url") or msg.get("url") or msg.get("file_url") or msg.get("image") or ""
        profile_pic_url = msg.get("profile_pic_url") or ""

        if profile_pic_url and profile_pic_url.startswith("/"):
            profile_pic_url = f"https://whats.dominuslabs.online{profile_pic_url}"
        if image_url and image_url.startswith("/"):
            image_url = f"https://whats.dominuslabs.online{image_url}"

        ts = msg.get("message_timestamp") or msg.get("created_at") or msg.get("timestamp") or msg.get("createdAt")

        mapped.append({
            "id": msg_id,
            "message_id": msg_id,
            "session_id": msg.get("session_id"),
            "contact_jid": msg.get("contact_jid"),
            "is_from_me": is_from_me,
            "sender": sender,
            "direction": direction,
            "sent_by_user": is_from_me,
            "message": raw_text,
            "content": raw_text,
            "caption": msg.get("caption", ""),
            "message_type": msg.get("message_type", "conversation"),
            "chat_kind": msg.get("chat_kind", "private"),
            "image_url": image_url,
            "media_url": image_url,
            "push_name": msg.get("push_name"),
            "display_phone": msg.get("display_phone"),
            "profile_pic_url": profile_pic_url,
            "channel": lead_channel,
            "timestamp": ts,
            "status": msg.get("status", "received")
        })
        return mapped

    # Support legacy composite message object
    msg_id = str(msg.get("id", ""))
    created_at = msg.get("createdAt") or msg.get("data") or msg.get("created_at")
    updated_at = msg.get("updatedAt") or msg.get("data") or msg.get("updated_at")

    user_text = msg.get("mensagem_enviada")
    if user_text is not None and str(user_text).strip().lower() not in ("null", ""):
        cleaned_text, embedded_ts = parse_embedded_timestamp(str(user_text).strip())
        mapped.append({
            "id": f"{msg_id}_user",
            "sender": "user",
            "direction": "outgoing",
            "sent_by_user": True,
            "message": cleaned_text,
            "content": cleaned_text,
            "channel": lead_channel,
            "timestamp": embedded_ts or created_at
        })
    elif msg.get("tipo") == "mensagem_enviada":
        mapped.append({
            "id": f"{msg_id}_user_fallback",
            "sender": "user",
            "direction": "outgoing",
            "sent_by_user": True,
            "message": "Mensagem enviada",
            "content": "Mensagem enviada",
            "channel": lead_channel,
            "timestamp": created_at
        })

    lead_text = msg.get("resposta")
    if lead_text is not None and str(lead_text).strip().lower() not in ("null", ""):
        cleaned_text, embedded_ts = parse_embedded_timestamp(str(lead_text).strip())
        mapped.append({
            "id": f"{msg_id}_lead",
            "sender": "lead",
            "direction": "incoming",
            "sent_by_user": False,
            "message": cleaned_text,
            "content": cleaned_text,
            "channel": lead_channel,
            "timestamp": embedded_ts or updated_at
        })

    return mapped

def update_raw_lead(raw_lead: dict, payload: dict) -> dict:
    """
    Updates a copy of the original raw lead with values from the frontend payload,
    preserving the exact key names and formats received from N8N.
    No new keys are added, and original keys that are not updated remain untouched.
    """
    res = copy.deepcopy(raw_lead)

    # Helper function to check and update keys at a given dict level
    def update_keys(d: dict, mappings: dict):
        for target_key, val in mappings.items():
            if target_key in d:
                d[target_key] = val

    # 1. Top level mappings
    top_mappings = {}
    
    # Name mappings
    name_val = payload.get("company_name")
    if name_val is not None:
        top_mappings["empresa_nome"] = name_val
        top_mappings["nome_empresa"] = name_val
        top_mappings["company_name"] = name_val

    # Phone mappings
    phone_val = payload.get("whatsapp")
    if phone_val is not None:
        top_mappings["telefone_contato"] = phone_val
        top_mappings["telefone"] = phone_val
        top_mappings["whatsapp"] = phone_val

    # Email mappings
    email_val = payload.get("email")
    if email_val is not None:
        top_mappings["email_contato"] = email_val
        top_mappings["email"] = email_val

    # Status
    status_val = payload.get("status")
    if status_val is not None:
        top_mappings["status"] = status_val

    # Origin
    origem_val = payload.get("origem") or payload.get("origin")
    if origem_val is not None:
        top_mappings["origem"] = origem_val
        top_mappings["origin"] = origem_val

    # Nicho/Segmento
    segmento_val = payload.get("segmento") or payload.get("nicho")
    if segmento_val is not None:
        top_mappings["nicho"] = segmento_val
        top_mappings["segmento"] = segmento_val

    # Proposal
    proposal_val = payload.get("proposal") or payload.get("proposta_inicial")
    if proposal_val is not None:
        top_mappings["proposta_inicial"] = proposal_val
        top_mappings["proposta_pronta"] = proposal_val
        top_mappings["proposal"] = proposal_val

    # Localizacao, score, temperatura, lid
    for k in ["localizacao", "score", "temperatura", "lid"]:
        if k in payload:
            top_mappings[k] = payload[k]

    # Notes / falha / dor
    notes_val = payload.get("notes")
    if notes_val is not None:
        top_mappings["notes"] = notes_val
        top_mappings["falha_identificada"] = notes_val
        top_mappings["dor_identificada"] = notes_val
    if "falha_identificada" in payload:
        top_mappings["falha_identificada"] = payload["falha_identificada"]

    # Responsible
    resp_val = payload.get("responsible")
    if resp_val is not None:
        top_mappings["responsible"] = resp_val
        top_mappings["responsavel"] = resp_val

    # Time tracking
    top_mappings["updated_at"] = datetime.utcnow().isoformat() + "Z"
    top_mappings["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    update_keys(res, top_mappings)

    # 2. Nested payload mappings
    if "payload" in res:
        raw_payload = res["payload"]
        is_str = isinstance(raw_payload, str)
        payload_dict = safe_parse_json(raw_payload) if is_str else (raw_payload or {})
        if not isinstance(payload_dict, dict):
            payload_dict = {}

        # Merge any updated keys from the incoming payload dict
        if "payload" in payload and isinstance(payload["payload"], dict):
            payload_dict.update(payload["payload"])

        p_mappings = {}
        if "email" in payload:
            p_mappings["email"] = payload["email"]
        elif "email_contato" in payload:
            p_mappings["email"] = payload["email_contato"]

        # CTA, site, formulario, anuncio
        if "presenca_digital_tem_cta" in payload:
            p_mappings["tem_cta"] = payload["presenca_digital_tem_cta"]
        if "tem_cta" in payload:
            p_mappings["tem_cta"] = payload["tem_cta"]
            
        if "presenca_digital_url_site" in payload:
            p_mappings["url_site"] = payload["presenca_digital_url_site"]
        if "url_site" in payload:
            p_mappings["url_site"] = payload["url_site"]

        if "presenca_digital_formulario_captacao" in payload:
            p_mappings["tem_formulario"] = payload["presenca_digital_formulario_captacao"]
        if "tem_formulario" in payload:
            p_mappings["tem_formulario"] = payload["tem_formulario"]

        if "id_anuncio_meta" in payload:
            p_mappings["id_anuncio_meta"] = payload["id_anuncio_meta"]

        if "tem_site_proprio" in payload:
            p_mappings["tem_site_proprio"] = payload["tem_site_proprio"]

        if "erros_identificados_site" in payload:
            p_mappings["erros_identificados_site"] = payload["erros_identificados_site"]

        update_keys(payload_dict, p_mappings)
        res["payload"] = json.dumps(payload_dict) if is_str else payload_dict

    # 3. Nested presenca_digital mappings
    if "presenca_digital" in res:
        raw_presenca = res["presenca_digital"]
        is_str = isinstance(raw_presenca, str)
        presenca_dict = safe_parse_json(raw_presenca) if is_str else (raw_presenca or {})
        if not isinstance(presenca_dict, dict):
            presenca_dict = {}

        pr_mappings = {}
        if "presenca_digital_url_site" in payload:
            pr_mappings["url_site"] = payload["presenca_digital_url_site"]
        elif "url_site" in payload:
            pr_mappings["url_site"] = payload["url_site"]

        if "presenca_digital_status_site" in payload:
            pr_mappings["status_site"] = payload["presenca_digital_status_site"]

        if "tem_site_proprio" in payload:
            pr_mappings["tem_site_proprio"] = payload["tem_site_proprio"]

        if "erros_identificados_site" in payload:
            pr_mappings["erros_identificados_site"] = payload["erros_identificados_site"]

        update_keys(presenca_dict, pr_mappings)

        # diagnostico_site within presenca_digital
        if "diagnostico_site" in presenca_dict:
            raw_diag = presenca_dict["diagnostico_site"]
            diag_is_str = isinstance(raw_diag, str)
            diag_dict = safe_parse_json(raw_diag) if diag_is_str else (raw_diag or {})
            if not isinstance(diag_dict, dict):
                diag_dict = {}

            diag_mappings = {}
            cta_val = payload.get("presenca_digital_tem_cta")
            if cta_val is not None:
                diag_mappings["tem cta"] = cta_val
                diag_mappings["tem_cta"] = cta_val

            url_abre_val = payload.get("presenca_digital_url_abre")
            if url_abre_val is not None:
                diag_mappings["url abre"] = url_abre_val
                diag_mappings["url_abre"] = url_abre_val

            demora_val = payload.get("presenca_digital_demora_abrir")
            if demora_val is not None:
                diag_mappings["demora pra abrir?"] = demora_val
                diag_mappings["demora_abrir"] = demora_val

            form_val = payload.get("presenca_digital_formulario_captacao")
            if form_val is not None:
                diag_mappings["tem formulario de captação?"] = form_val
                diag_mappings["formulario_captacao"] = form_val

            update_keys(diag_dict, diag_mappings)
            presenca_dict["diagnostico_site"] = json.dumps(diag_dict) if diag_is_str else diag_dict

        res["presenca_digital"] = json.dumps(presenca_dict) if is_str else presenca_dict

    # 4. Nested reputacao_google mappings
    if "reputacao_google" in res:
        raw_rep = res["reputacao_google"]
        is_str = isinstance(raw_rep, str)
        rep_dict = safe_parse_json(raw_rep) if is_str else (raw_rep or {})
        if not isinstance(rep_dict, dict):
            rep_dict = {}

        rep_mappings = {}
        if "reputacao_google_nota_media" in payload:
            val = payload["reputacao_google_nota_media"]
            try:
                rep_mappings["nota_media"] = float(val) if val is not None else None
            except ValueError:
                rep_mappings["nota_media"] = val

        if "reputacao_google_total_avaliacoes" in payload:
            val = payload["reputacao_google_total_avaliacoes"]
            try:
                rep_mappings["total_avaliacoes"] = int(val) if val is not None else None
            except ValueError:
                rep_mappings["total_avaliacoes"] = val

        update_keys(rep_dict, rep_mappings)
        res["reputacao_google"] = json.dumps(rep_dict) if is_str else rep_dict

    # 5. Nested oportunidades_identificadas mappings
    if "oportunidades_identificadas" in res:
        raw_op = res["oportunidades_identificadas"]
        is_str = isinstance(raw_op, str)
        op_dict = safe_parse_json(raw_op) if is_str else (raw_op or {})
        if not isinstance(op_dict, dict):
            op_dict = {}

        op_mappings = {}
        if "oportunidades_identificadas_telefone_fixo" in payload:
            op_mappings["telefone_fixo"] = payload["oportunidades_identificadas_telefone_fixo"]

        urg_site_val = payload.get("oportunidades_identificadas_urgencia_site")
        if urg_site_val is not None:
            op_mappings["urgencia_de_site"] = urg_site_val
            op_mappings["urgencia_site"] = urg_site_val

        urg_av_val = payload.get("oportunidades_identificadas_urgencia_avaliacoes")
        if urg_av_val is not None:
            op_mappings["urgencia_de_avaliacoes"] = urg_av_val
            op_mappings["urgencia_avaliacoes"] = urg_av_val

        urg_rep_val = payload.get("oportunidades_identificadas_urgencia_gestao_reputacao")
        if urg_rep_val is not None:
            op_mappings["urgencia_de_gestao_reputacao"] = urg_rep_val
            op_mappings["urgencia_gestao_reputacao"] = urg_rep_val

        update_keys(op_dict, op_mappings)
        res["oportunidades_identificadas"] = json.dumps(op_dict) if is_str else op_dict

    return res

def sanitize_outgoing_payload(payload: dict) -> dict:
    """
    Filters the outgoing payload to contain ONLY whitelisted Portuguese keys.
    """
    whitelist = {
        "lead_id", "origem", "data_coleta", "nicho", "status", "empresa_nome",
        "telefone_contato", "email_contato", "localizacao", "score", "temperatura",
        "payload", "created_at", "updated_at", "proposta_inicial", "lid",
        "alterado_por", "updated_by"
    }
    
    sanitized = {}
    for k, v in payload.items():
        if k in whitelist:
            sanitized[k] = v

    # Sanitize nested payload dict if present
    if "payload" in sanitized:
        raw_p = sanitized["payload"]
        is_str = isinstance(raw_p, str)
        p_dict = safe_parse_json(raw_p) if is_str else (raw_p or {})
        if isinstance(p_dict, dict):
            # Preserve all keys inside the dynamic payload dictionary
            sanitized["payload"] = json.dumps(p_dict) if is_str else p_dict

    return sanitized

def normalize_session_name(name: str) -> str:
    if not name:
        return ""
    return name.lower().replace("-", "").replace("_", "").replace(" ", "")

def unpack_n8n_raw_leads(raw_leads: List[dict]) -> List[dict]:
    if not isinstance(raw_leads, list):
        return []

    unpacked = []
    for item in raw_leads:
        if not isinstance(item, dict):
            continue

        c_jid = item.get("contact_jid") or item.get("jid") or ""
        s_id = item.get("session_id") or item.get("whatsapp_instance") or ""

        if "contacts" in item and isinstance(item["contacts"], list):
            top_session_id = item.get("session_id", "")
            for c in item["contacts"]:
                if not isinstance(c, dict):
                    continue
                c_copy = copy.deepcopy(c)
                c_jid_inner = c_copy.get("contact_jid") or c_copy.get("jid") or c_copy.get("id") or ""
                c_session_id = c_copy.get("session_id") or top_session_id
                c_copy["session_id"] = c_session_id
                c_copy["whatsapp_instance"] = c_session_id

                if c_jid_inner and c_session_id and c_session_id != "default":
                    group_key = f"{c_jid_inner}___{c_session_id}"
                else:
                    group_key = c_jid_inner or "unknown_lead"

                c_copy["id"] = group_key
                c_copy["lead_id"] = group_key

                pic = c_copy.get("profile_pic_url")
                if pic and pic.startswith("/"):
                    c_copy["profile_pic_url"] = f"https://whats.dominuslabs.online{pic}"

                unpacked.append(c_copy)
            continue

        if "conversations" in item and isinstance(item["conversations"], list):
            top_session_id = item.get("session_id", "")
            for conv in item["conversations"]:
                if not isinstance(conv, dict):
                    continue
                c_copy = copy.deepcopy(conv)
                c_jid_inner = c_copy.get("contact_jid") or c_copy.get("jid") or c_copy.get("id") or ""
                c_session_id = c_copy.get("session_id") or top_session_id
                c_copy["session_id"] = c_session_id
                c_copy["whatsapp_instance"] = c_session_id

                if c_jid_inner and c_session_id and c_session_id != "default":
                    group_key = f"{c_jid_inner}___{c_session_id}"
                else:
                    group_key = c_jid_inner or "unknown_lead"

                c_copy["id"] = group_key
                c_copy["lead_id"] = group_key

                pic = c_copy.get("profile_pic_url")
                if pic and pic.startswith("/"):
                    c_copy["profile_pic_url"] = f"https://whats.dominuslabs.online{pic}"

                unpacked.append(c_copy)
            continue

        if "mensagens" in item and isinstance(item["mensagens"], list) and len(item["mensagens"]) > 0 and not c_jid:
            top_session_id = item.get("session_id", "")
            contacts_map = {}
            for m in item["mensagens"]:
                if not isinstance(m, dict):
                    continue

                m_c_jid = m.get("contact_jid") or m.get("jid") or ""
                if not m_c_jid:
                    m_c_jid = m.get("push_name") or m.get("display_phone") or "unknown_contact"

                m_session_id = m.get("session_id") or top_session_id or ""
                group_key = f"{m_c_jid}___{m_session_id}" if m_session_id else m_c_jid

                if group_key not in contacts_map:
                    profile_pic = m.get("profile_pic_url") or item.get("profile_pic_url") or ""
                    if profile_pic and profile_pic.startswith("/"):
                        profile_pic = f"https://whats.dominuslabs.online{profile_pic}"

                    contacts_map[group_key] = {
                        "id": group_key,
                        "jid": m_c_jid,
                        "contact_jid": m_c_jid,
                        "push_name": m.get("push_name") or item.get("push_name") or "Contato Sem Nome",
                        "display_phone": m.get("display_phone") or item.get("display_phone") or "",
                        "profile_pic_url": profile_pic,
                        "session_id": m_session_id,
                        "whatsapp_instance": m_session_id,
                        "created_at": m.get("created_at") or m.get("message_timestamp") or item.get("created_at"),
                        "mensagens": []
                    }

                if m.get("push_name") and m.get("push_name") != "Desconhecido":
                    contacts_map[group_key]["push_name"] = m.get("push_name")
                if m.get("display_phone"):
                    contacts_map[group_key]["display_phone"] = m.get("display_phone")
                if m.get("profile_pic_url") and m.get("profile_pic_url") != "changed":
                    pic = m.get("profile_pic_url")
                    if pic and pic.startswith("/"):
                        pic = f"https://whats.dominuslabs.online{pic}"
                    contacts_map[group_key]["profile_pic_url"] = pic

                contacts_map[group_key]["mensagens"].append(m)

            for c_info in contacts_map.values():
                unpacked.append(c_info)
        else:
            item_copy = copy.deepcopy(item)
            nested_msgs = item.get("messages") if isinstance(item.get("messages"), list) else (item.get("mensagens") if isinstance(item.get("mensagens"), list) else [])
            for m in nested_msgs:
                if isinstance(m, dict):
                    m_pname = m.get("push_name")
                    if m_pname and isinstance(m_pname, str) and m_pname.strip() and m_pname.strip().lower() not in ("desconhecido", "unknown", "null", "none") and "@lid" not in m_pname.lower() and "@s.whatsapp.net" not in m_pname.lower():
                        if not item_copy.get("push_name"):
                            item_copy["push_name"] = m_pname.strip()

                    m_phone = m.get("display_phone") or m.get("whatsapp")
                    if m_phone and not item_copy.get("display_phone"):
                        item_copy["display_phone"] = m_phone.strip()

                    m_pic = m.get("profile_pic_url") or m.get("avatar")
                    if m_pic and m_pic != "changed" and str(m_pic).lower() not in ("null", "none", "") and not item_copy.get("profile_pic_url"):
                        if str(m_pic).startswith("/"):
                            m_pic = f"https://whats.dominuslabs.online{m_pic}"
                        item_copy["profile_pic_url"] = str(m_pic)

            if c_jid and s_id and s_id != "default":
                group_key = f"{c_jid}___{s_id}"
                item_copy["id"] = group_key
                item_copy["lead_id"] = group_key
            unpacked.append(item_copy)

    return unpacked

class ProgressiveContactCache:
    """
    Thread-safe in-memory progressive cache keyed by contact_jid.
    Maintains profile state across 3 requests:
    Request 1 (Basic Info from contacts table)
    -> Request 2 (Inbox State from conversations table)
    -> Request 3 (Chat History from messages table).
    """
    _cache: Dict[str, dict] = {}

    @classmethod
    def get(cls, jid: str) -> Optional[dict]:
        if not jid:
            return None
        return cls._cache.get(jid)

    @classmethod
    def set_contact(cls, jid: str, contact_data: dict) -> dict:
        if not jid:
            return contact_data
        existing = cls._cache.get(jid, {})
        existing.update({
            "contact_jid": jid,
            "push_name": contact_data.get("push_name") or existing.get("push_name") or "Contato Sem Nome",
            "profile_pic_url": contact_data.get("profile_pic_url") or existing.get("profile_pic_url") or "",
            "display_phone": contact_data.get("display_phone") or existing.get("display_phone") or "",
            "whatsapp": contact_data.get("whatsapp") or existing.get("whatsapp") or "",
            "email": contact_data.get("email") or existing.get("email") or "",
            "status": contact_data.get("status") or existing.get("status") or "Prospectado",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        for k in ("session_id", "unread_count", "last_message_preview", "mensagens", "messages"):
            if k in contact_data:
                existing[k] = contact_data[k]
        cls._cache[jid] = existing
        return existing

    @classmethod
    def set_conversation(cls, jid: str, conv_data: dict) -> dict:
        if not jid:
            return conv_data
        existing = cls._cache.get(jid, {"contact_jid": jid})
        existing["session_id"] = conv_data.get("session_id") or existing.get("session_id", "default")
        existing["unread_count"] = conv_data.get("unread_count", 0)
        existing["last_message_preview"] = conv_data.get("last_message_preview") or conv_data.get("content", "")
        if conv_data.get("push_name") and conv_data.get("push_name") not in ("Desconhecido", "Contato Sem Nome"):
            existing["push_name"] = conv_data["push_name"]
        if conv_data.get("profile_pic_url"):
            existing["profile_pic_url"] = conv_data["profile_pic_url"]
        existing["updated_at"] = datetime.utcnow().isoformat() + "Z"
        cls._cache[jid] = existing
        return existing

    @classmethod
    def set_messages(cls, jid: str, messages_list: List[dict]) -> dict:
        if not jid:
            return {}
        existing = cls._cache.get(jid, {"contact_jid": jid})
        existing["mensagens"] = messages_list
        existing["messages"] = messages_list
        existing["has_messages"] = len(messages_list) > 0
        existing["updated_at"] = datetime.utcnow().isoformat() + "Z"
        cls._cache[jid] = existing
        return existing

    @classmethod
    def get_assembled_payload(cls, jid: str) -> dict:
        return cls._cache.get(jid, {"contact_jid": jid, "mensagens": []})

    @classmethod
    def clear(cls):
        cls._cache.clear()

class N8NService:
    # Leads cache state
    _leads_cache = None
    _leads_cache_time = 0.0
    _leads_cache_url = None
    CACHE_TTL = 10.0  # seconds

    @staticmethod
    def invalidate_leads_cache():
        N8NService._leads_cache = None
        N8NService._leads_cache_time = 0.0
        N8NService._leads_cache_url = None
        logger.info("CRM Leads Cache explicitly invalidated.")

    @staticmethod
    async def run_scrapper(payload: dict, platform: str = "meta_ads") -> dict:
        fallback_url = settings.SCRAPPER_META_WEBHOOK_URL if platform == "meta_ads" else settings.SCRAPPER_MAPS_WEBHOOK_URL
        url = payload.get("webhook_url") or fallback_url
        if not url:
            logger.info("SCRAPPER Webhook URL not configured. Returning mock success.")
            return {"status": "success", "message": "Scrapper triggered (MOCK Mode)", "data": payload}

        outgoing_payload = {
            "queries": payload.get("queries", []),
            "min_results": payload.get("min_results", 10),
            "max_results": payload.get("max_results", 20),
        }
        if "target_platform" in payload and payload["target_platform"]:
            outgoing_payload["target_platform"] = payload["target_platform"]
            # If target_platform is whatsapp or instagram, also set contact_channel for maximum N8N compatibility
            if payload["target_platform"] in ("whatsapp", "instagram"):
                outgoing_payload["contact_channel"] = payload["target_platform"]
        if "contact_channel" in payload and payload["contact_channel"]:
            outgoing_payload["contact_channel"] = payload["contact_channel"]
        if "objective" in payload and payload["objective"]:
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
        # Check cache
        if N8NService._leads_cache is not None:
            if time.time() - N8NService._leads_cache_time < N8NService.CACHE_TTL:
                if N8NService._leads_cache_url == url:
                    logger.info("Returning CRM Leads from in-memory cache.")
                    return N8NService._leads_cache

        if not url:
            logger.info("CRM_GET_LEADS_WEBHOOK_URL not configured. Returning mock leads.")
            mapped_mock = [map_n8n_lead(l) for l in MOCK_LEADS]
            mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
            mapped_mock.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
            N8NService._leads_cache = mapped_mock
            N8NService._leads_cache_time = time.time()
            N8NService._leads_cache_url = url
            return mapped_mock

        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=get_contacts"

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
                elif isinstance(data, dict) and "mensagens" in data:
                    raw_leads = [data]
            except Exception as e:
                logger.error(f"Error calling GET leads webhook: {e}. Falling back to mock data.", exc_info=True)

        if not raw_leads:
            mapped_mock = [map_n8n_lead(l) for l in MOCK_LEADS]
            mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
            mapped_mock.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
            for m in mapped_mock:
                c_jid = m.get("contact_jid") or m.get("jid") or m.get("id")
                if c_jid:
                    ProgressiveContactCache.set_contact(c_jid, m)
            N8NService._leads_cache = mapped_mock
            N8NService._leads_cache_time = time.time()
            N8NService._leads_cache_url = url
            return mapped_mock

        raw_leads = unpack_n8n_raw_leads(raw_leads)
        mapped_leads = [map_n8n_lead(l) for l in raw_leads if isinstance(l, dict)]
        mapped_leads.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
        mapped_leads.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
        
        # Step 1: Cache basic info by contact_jid
        for m in mapped_leads:
            c_jid = m.get("contact_jid") or m.get("jid") or m.get("id")
            if c_jid:
                ProgressiveContactCache.set_contact(c_jid, m)

        N8NService._leads_cache = mapped_leads
        N8NService._leads_cache_time = time.time()
        N8NService._leads_cache_url = url
        return mapped_leads

    @staticmethod
    async def get_conversations() -> List[dict]:
        """
        Obtém a lista de conversas ativas via action=get_conversations no webhook CRM.
        """
        url = settings.CRM_GET_MESSAGES_WEBHOOK_URL or settings.CRM_GET_LEADS_WEBHOOK_URL
        if not url:
            return []

        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=get_conversations"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(endpoint_url, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                raw_convs = []
                if isinstance(data, list):
                    raw_convs = data
                elif isinstance(data, dict):
                    raw_convs = data.get("conversas") or data.get("conversations") or data.get("leads") or [data]
                
                unpacked = unpack_n8n_raw_leads(raw_convs)
                mapped = [map_n8n_lead(l) for l in unpacked if isinstance(l, dict)]
                
                # Step 2: Append conversation inbox state to cached contact profile
                for m in mapped:
                    c_jid = m.get("contact_jid") or m.get("jid") or m.get("id")
                    if c_jid:
                        ProgressiveContactCache.set_conversation(c_jid, m)

                return mapped
            except Exception as e:
                logger.error(f"Error calling GET conversations webhook: {e}")
                return []

    @staticmethod
    async def get_chat_history(lead_id: str) -> List[dict]:
        """
        Alias para get_messages utilizando action=get_chat_history.
        """
        return await N8NService.get_messages(lead_id)

    @staticmethod
    async def update_lead(lead_id: str, payload: dict, current_user: str = None) -> dict:
        N8NService.invalidate_leads_cache()
        url = settings.CRM_UPDATE_LEAD_WEBHOOK_URL

        # Try to find in cache
        raw_lead = None
        if lead_id in RAW_LEADS_CACHE:
            raw_lead = copy.deepcopy(RAW_LEADS_CACHE[lead_id])

        if not raw_lead:
            # Fallback template with Portuguese keys if not in cache
            raw_lead = {
                "lead_id": lead_id,
                "origem": payload.get("origem") or "",
                "data_coleta": payload.get("created_at") or None,
                "nicho": payload.get("segmento") or "",
                "status": payload.get("status") or "Prospectado",
                "empresa_nome": payload.get("company_name") or "",
                "telefone_contato": payload.get("whatsapp") or "",
                "email_contato": payload.get("email") or "",
                "localizacao": payload.get("localizacao") or None,
                "score": payload.get("score") or None,
                "temperatura": payload.get("temperatura") or None,
                "payload": {
                    "email": payload.get("email") or None,
                    "tem_cta": payload.get("presenca_digital_tem_cta") or "não",
                    "url_site": payload.get("url_site") or None,
                    "tem_formulario": payload.get("presenca_digital_formulario_captacao") or "não",
                    "id_anuncio_meta": payload.get("id_anuncio_meta") or None,
                    "tem_site_proprio": payload.get("tem_site_proprio") if payload.get("tem_site_proprio") is not None else False,
                    "erros_identificados_site": payload.get("erros_identificados_site") or None
                },
                "created_at": payload.get("created_at") or None,
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "proposta_inicial": payload.get("proposal") or "",
                "lid": payload.get("lid") or None
            }

        # Update the raw lead copy
        outgoing_payload = update_raw_lead(raw_lead, payload)

        if current_user:
            outgoing_payload["alterado_por"] = current_user
            outgoing_payload["updated_by"] = current_user

        # Sanitize outgoing payload to contain ONLY Portuguese keys
        outgoing_payload = sanitize_outgoing_payload(outgoing_payload)

        # Update in cache for subsequent calls
        RAW_LEADS_CACHE[lead_id] = copy.deepcopy(outgoing_payload)

        # Also update mock leads for local consistency/fallback
        reconstructed_payload_meta = {}
        if isinstance(outgoing_payload.get("payload"), dict):
            reconstructed_payload_meta = outgoing_payload["payload"]
        elif isinstance(outgoing_payload.get("payload"), str):
            reconstructed_payload_meta = safe_parse_json(outgoing_payload["payload"])

        reconstructed_presenca = {}
        if isinstance(outgoing_payload.get("presenca_digital"), dict):
            reconstructed_presenca = outgoing_payload["presenca_digital"]
        elif isinstance(outgoing_payload.get("presenca_digital"), str):
            reconstructed_presenca = safe_parse_json(outgoing_payload["presenca_digital"])

        reconstructed_reputacao = {}
        if isinstance(outgoing_payload.get("reputacao_google"), dict):
            reconstructed_reputacao = outgoing_payload["reputacao_google"]
        elif isinstance(outgoing_payload.get("reputacao_google"), str):
            reconstructed_reputacao = safe_parse_json(outgoing_payload["reputacao_google"])

        reconstructed_oportunidades = {}
        if isinstance(outgoing_payload.get("oportunidades_identificadas"), dict):
            reconstructed_oportunidades = outgoing_payload["oportunidades_identificadas"]
        elif isinstance(outgoing_payload.get("oportunidades_identificadas"), str):
            reconstructed_oportunidades = safe_parse_json(outgoing_payload["oportunidades_identificadas"])

        for i, lead in enumerate(MOCK_LEADS):
            if lead["id"] == lead_id:
                for k, v in payload.items():
                    lead[k] = v
                lead["payload"] = reconstructed_payload_meta
                lead["presenca_digital"] = reconstructed_presenca
                lead["reputacao_google"] = reconstructed_reputacao
                lead["oportunidades_identificadas"] = reconstructed_oportunidades
                lead["last_interaction"] = datetime.utcnow().isoformat() + "Z"
                if current_user:
                    lead["alterado_por"] = current_user
                    lead["updated_by"] = current_user
                MOCK_LEADS[i] = lead
                break

        if not url:
            logger.info("CRM_UPDATE_LEAD_WEBHOOK_URL not configured. Lead updated locally in-memory.")
            updated_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
            mapped = map_n8n_lead(updated_lead) if updated_lead else map_n8n_lead({"id": lead_id, **payload})
            if current_user:
                mapped["alterado_por"] = current_user
                mapped["updated_by"] = current_user
            return mapped

        # Append action parameter to CRM N8N query parameters
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=update_lead&id={lead_id}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.put(endpoint_url, json=outgoing_payload, timeout=30.0)
                response.raise_for_status()
                res_data = clean_n8n_response(response.json())
                if isinstance(res_data, dict) and ("company_name" in res_data or "nome_empresa" in res_data or "empresa_nome" in res_data):
                    mapped = map_n8n_lead(res_data)
                else:
                    fallback_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
                    if fallback_lead:
                        mapped = map_n8n_lead(fallback_lead)
                    else:
                        mapped = map_n8n_lead({"id": lead_id, **payload})
                
                if current_user:
                    mapped["alterado_por"] = current_user
                    mapped["updated_by"] = current_user
                return mapped
            except Exception as e:
                logger.error(f"Error calling UPDATE lead webhook: {e}")
                fallback_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id), None)
                if fallback_lead:
                    mapped = map_n8n_lead(fallback_lead)
                else:
                    mapped = map_n8n_lead({"id": lead_id, **payload})
                    
                if current_user:
                    mapped["alterado_por"] = current_user
                    mapped["updated_by"] = current_user
                return mapped

    @staticmethod
    async def delete_lead(lead_id: str) -> dict:
        N8NService.invalidate_leads_cache()
        url = settings.CRM_UPDATE_LEAD_WEBHOOK_URL

        # Remove from mock lists (MOCK_LEADS, RAW_LEADS_CACHE, MOCK_CONVERSATIONS, MOCK_ACTIVITIES)
        for i, lead in enumerate(MOCK_LEADS):
            if str(lead.get("id")) == str(lead_id):
                MOCK_LEADS.pop(i)
                break
        
        for k in list(RAW_LEADS_CACHE.keys()):
            if str(k) == str(lead_id):
                del RAW_LEADS_CACHE[k]

        for k in list(MOCK_CONVERSATIONS.keys()):
            if str(k) == str(lead_id):
                del MOCK_CONVERSATIONS[k]
            
        for k in list(MOCK_ACTIVITIES.keys()):
            if str(k) == str(lead_id):
                del MOCK_ACTIVITIES[k]

        if not url:
            logger.info("CRM_UPDATE_LEAD_WEBHOOK_URL not configured. Lead deleted locally in-memory.")
            return {"status": "success", "message": "Lead deleted locally (MOCK Mode)", "id": lead_id}

        # Append action parameter to CRM N8N query parameters (using same update URL)
        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=delete_lead&id={lead_id}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.delete(endpoint_url, timeout=30.0)
                response.raise_for_status()
                try:
                    res_data = clean_n8n_response(response.json())
                    if isinstance(res_data, dict):
                        return res_data
                except Exception:
                    pass
                return {"status": "success", "id": lead_id}
            except Exception as e:
                logger.error(f"Error calling DELETE lead webhook: {e}")
                return {"status": "success", "message": f"Deleted locally. API Error: {str(e)}", "id": lead_id}

    @staticmethod
    async def get_messages(lead_id: str) -> List[dict]:
        all_msgs = list(MOCK_CONVERSATIONS.get(lead_id, []))
        url = settings.CRM_GET_MESSAGES_WEBHOOK_URL

        target_id_str = str(lead_id).strip()
        target_jid = target_id_str
        target_session = None
        if "___" in target_id_str:
            parts = target_id_str.split("___", 1)
            target_jid = parts[0]
            target_session = parts[1]

        cached_lead = RAW_LEADS_CACHE.get(lead_id)
        if not cached_lead:
            cached_lead = RAW_LEADS_CACHE.get(target_jid)
        if cached_lead and "mensagens" in cached_lead and isinstance(cached_lead["mensagens"], list):
            embedded_msgs = []
            seen_keys = set()
            lead_channel = cached_lead.get("origin", "whatsapp").lower()
            for m in cached_lead["mensagens"]:
                if not isinstance(m, dict):
                    continue
                mapped_list = map_n8n_message(m, lead_channel)
                for mapped_msg in mapped_list:
                    msg_id = str(mapped_msg.get("id") or mapped_msg.get("message_id") or "")
                    content = str(mapped_msg.get("content") or mapped_msg.get("message") or "").strip()
                    is_from_me = mapped_msg.get("is_from_me", False)
                    ts = str(mapped_msg.get("timestamp") or mapped_msg.get("message_timestamp") or "")

                    if msg_id and not msg_id.startswith("temp_") and msg_id.lower() not in ("none", "null", ""):
                        dedup_key = f"id:{msg_id}"
                    else:
                        dedup_key = f"msg:{content}:{is_from_me}:{ts[:16]}"

                    if dedup_key not in seen_keys:
                        seen_keys.add(dedup_key)
                        embedded_msgs.append(mapped_msg)

            embedded_msgs.sort(key=lambda x: x.get("timestamp") or "")
            if len(embedded_msgs) > 0:
                MOCK_CONVERSATIONS[lead_id] = embedded_msgs

        if not url:
            return MOCK_CONVERSATIONS.get(lead_id, all_msgs)

        lid = None
        if cached_lead:
            lid = cached_lead.get("lid") or cached_lead.get("LID") or cached_lead.get("Lid")

        sep = "&" if "?" in url else "?"
        endpoint_url = f"{url}{sep}action=get_chat_history&lead_id={target_jid}"
        if lid:
            endpoint_url += f"&lid={lid}"
        if target_session:
            endpoint_url += f"&session_id={target_session}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(endpoint_url, timeout=30.0)
                response.raise_for_status()
                body = response.text.strip()
                raw_msgs = []
                if body:
                    data = response.json()
                    if isinstance(data, list):
                        for d in data:
                            if isinstance(d, dict):
                                d_sess = str(d.get("session_id") or d.get("whatsapp_instance") or "")
                                if target_session and d_sess and normalize_session_name(d_sess) != normalize_session_name(target_session):
                                    continue
                                if "mensagens" in d and isinstance(d["mensagens"], list):
                                    raw_msgs.extend(d["mensagens"])
                                else:
                                    raw_msgs.append(d)
                    elif isinstance(data, dict):
                        raw_msgs = data.get("messages") or data.get("conversas") or data.get("historico") or data.get("history") or []
                        if not isinstance(raw_msgs, list):
                            raw_msgs = [data]

                lead_channel = "whatsapp"
                if cached_lead and cached_lead.get("origin"):
                    lead_channel = cached_lead["origin"].lower()

                fresh_msgs = []
                seen_keys = set()

                for m in raw_msgs:
                    if isinstance(m, dict):
                        mapped_list = map_n8n_message(m, lead_channel)
                        for mapped_msg in mapped_list:
                            msg_session = str(mapped_msg.get("session_id") or m.get("session_id") or "")
                            if target_session and msg_session:
                                if normalize_session_name(msg_session) != normalize_session_name(target_session):
                                    continue

                            msg_id = str(mapped_msg.get("id") or mapped_msg.get("message_id") or "")
                            content = str(mapped_msg.get("content") or mapped_msg.get("message") or "").strip()
                            is_from_me = mapped_msg.get("is_from_me", False)
                            ts = str(mapped_msg.get("timestamp") or mapped_msg.get("message_timestamp") or "")

                            if msg_id and not msg_id.startswith("temp_") and msg_id.lower() not in ("none", "null", ""):
                                dedup_key = f"id:{msg_id}"
                            else:
                                dedup_key = f"msg:{content}:{is_from_me}:{ts[:16]}"

                            if dedup_key not in seen_keys:
                                seen_keys.add(dedup_key)
                                fresh_msgs.append(mapped_msg)

                fresh_msgs.sort(key=lambda x: x.get("timestamp") or "")
                
                # Step 3: Append full chat history to cached contact profile
                ProgressiveContactCache.set_messages(target_jid, fresh_msgs)

                if len(fresh_msgs) > 0:
                    MOCK_CONVERSATIONS[lead_id] = fresh_msgs
                    return fresh_msgs

                return MOCK_CONVERSATIONS.get(lead_id, [])
            except Exception as e:
                logger.error(f"Error calling GET messages webhook: {e}. Returning cached.")
                return MOCK_CONVERSATIONS.get(lead_id, all_msgs)

    @staticmethod
    def _extract_n8n_error_message(resp_data) -> Optional[str]:
        import json
        try:
            if isinstance(resp_data, list) and len(resp_data) > 0:
                item = resp_data[0]
            else:
                item = resp_data

            if isinstance(item, dict) and "error" in item:
                err_obj = item["error"]
                if isinstance(err_obj, dict):
                    inner_msg = err_obj.get("message") or err_obj.get("detail") or ""
                    if isinstance(inner_msg, str):
                        if " - " in inner_msg:
                            parts = inner_msg.split(" - ", 1)
                            potential_json = parts[1].strip()
                            try:
                                decoded_str = json.loads(potential_json)
                                if isinstance(decoded_str, str):
                                    decoded_data = json.loads(decoded_str)
                                else:
                                    decoded_data = decoded_str
                                    
                                if isinstance(decoded_data, dict):
                                    return decoded_data.get("message") or decoded_data.get("error") or inner_msg
                            except Exception:
                                pass
                        return inner_msg
            if isinstance(resp_data, dict):
                return resp_data.get("message") or resp_data.get("error") or str(resp_data)
        except Exception:
            pass
        return None

    @staticmethod
    async def send_whatsapp_message(payload: dict) -> dict:
        url = settings.CRM_SEND_WHATSAPP_WEBHOOK_URL
        lead_id = payload.get("lead_id")
        message_text = payload.get("message")
        phone = payload.get("phone", "")

        # Clean phone number to digits-only for standard whatsapp api gateways
        cleaned_phone = "".join(c for c in phone if c.isdigit())

        # Resolve lid from cache or lead list if present
        lid = None
        if lead_id in RAW_LEADS_CACHE:
            cached = RAW_LEADS_CACHE[lead_id]
            lid = cached.get("lid") or cached.get("LID") or cached.get("Lid")
        
        if not lid:
            try:
                leads = await N8NService.get_leads()
                lead_obj = next((l for l in leads if str(l.get("id")) == str(lead_id)), None)
                if lead_obj:
                    lid = lead_obj.get("lid")
                    if not lid and lead_id in RAW_LEADS_CACHE:
                        cached = RAW_LEADS_CACHE[lead_id]
                        lid = cached.get("lid") or cached.get("LID") or cached.get("Lid")
            except Exception:
                pass

        # Helper to update local mock lists upon successful send
        def update_local_mock_state(msg_id: str, text: str, timestamp: str):
            N8NService.invalidate_leads_cache()
            msg = {
                "id": msg_id,
                "sender": "user",
                "message": text,
                "channel": "whatsapp",
                "timestamp": timestamp
            }
            if lead_id not in MOCK_CONVERSATIONS:
                MOCK_CONVERSATIONS[lead_id] = []
            MOCK_CONVERSATIONS[lead_id].append(msg)

            # Update last interaction timestamp on lead
            for lead in MOCK_LEADS:
                if lead["id"] == lead_id:
                    lead["last_interaction"] = timestamp
                    break

            # Log event message_sent
            act = {
                "lead_id": lead_id,
                "event_type": "message_sent",
                "timestamp": timestamp,
                "metadata": {"message": text, "channel": "whatsapp"}
            }
            if lead_id not in MOCK_ACTIVITIES:
                MOCK_ACTIVITIES[lead_id] = []
            MOCK_ACTIVITIES[lead_id].append(act)
            return msg

        default_id = f"msg_{int(datetime.utcnow().timestamp())}"
        default_ts = datetime.utcnow().isoformat() + "Z"

        if not url:
            logger.info("CRM_SEND_WHATSAPP_WEBHOOK_URL not configured. Message logged locally in-memory.")
            return update_local_mock_state(default_id, message_text, default_ts)

        # Match Evolution API payload structure as well as direct params
        outgoing_payload = {
            "jid": cleaned_phone,
            "text": message_text,
            "number": cleaned_phone,
            "body": message_text,
            "phone": phone,
            "message": message_text,
            "lead_id": lead_id
        }
        if lid:
            outgoing_payload["lid"] = lid
        if payload.get("updated_by"):
            outgoing_payload["updated_by"] = payload["updated_by"]
            outgoing_payload["alterado_por"] = payload["updated_by"]
        if payload.get("whatsapp_token"):
            outgoing_payload["whatsapp_token"] = payload["whatsapp_token"]
        if payload.get("session_id"):
            outgoing_payload["session_id"] = payload["session_id"]
            public_url = getattr(settings, "WHATSAPP_PUBLIC_URL", "https://whats.dominuslabs.online").rstrip("/")
            if "hkossco0sgg" in public_url or "localhost" in public_url or "10.0.1." in public_url:
                public_url = "https://whats.dominuslabs.online"
            outgoing_payload["whatsapp_api_url"] = public_url
            outgoing_payload["whatsapp_send_url"] = f"{public_url}/api/sessions/{payload['session_id']}/messages/send"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(url, json=outgoing_payload, timeout=30.0)
                
                # Check for the specific authentication error format returned by n8n
                is_auth_error = False
                try:
                    if response.status_code == 401:
                        is_auth_error = True
                    else:
                        resp_text = response.text
                        if any(kw in resp_text.lower() for kw in ["401", "unauthorized", "invalid_token", "token verification failed", "missing token"]):
                            is_auth_error = True
                except Exception:
                    pass

                if is_auth_error:
                    print("[M2M-AUTH-FLOW] >>> Detectado erro de autenticação n8n no corpo da resposta.", flush=True)
                    raise ValueError("AUTH_ERROR_N8N_BAD_REQUEST")

                if response.status_code >= 400:
                    # Try to extract detailed error message from response body
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        resp_data = response.json()
                        extracted_msg = N8NService._extract_n8n_error_message(resp_data)
                        if extracted_msg:
                            error_msg = extracted_msg
                        elif isinstance(resp_data, dict):
                            error_msg = resp_data.get("message") or resp_data.get("error") or response.text
                    except Exception:
                        error_msg = response.text or error_msg
                    raise ValueError(error_msg)
                
                # Success path
                N8NService.invalidate_leads_cache()
                msg_id = default_id
                msg_text = message_text
                msg_ts = default_ts
                
                try:
                    res_json = clean_n8n_response(response.json())
                    msg_data = res_json.get("message") if isinstance(res_json, dict) else None
                    if isinstance(msg_data, dict):
                        msg_id = msg_data.get("id") or msg_id
                        msg_text = msg_data.get("text") or msg_data.get("message") or msg_text
                        ts_val = msg_data.get("timestamp")
                        if ts_val:
                            try:
                                msg_ts = datetime.fromtimestamp(float(ts_val)).isoformat() + "Z"
                            except Exception:
                                pass
                except Exception:
                    pass
                
                return update_local_mock_state(msg_id, msg_text, msg_ts)
            except ValueError:
                raise
            except Exception as e:
                logger.error(f"Error calling SEND whatsapp message webhook: {e}")
                raise ValueError(f"Falha de conexão com a API do WhatsApp: {str(e)}")

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
