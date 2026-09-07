"""
Documentação do módulo n8n_service.py.

O que faz: Implementa a lógica estrutural e funcional para o serviço de domínio n8n_service.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o serviço de domínio n8n_service funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
import httpx
import logging
import json
import copy
import re
import time
import os
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.crypto import encrypt_payload, decrypt_payload
from datetime import datetime, timezone

RAW_LEADS_CACHE = {}

KNOWN_CONTACT_NAMES = {
    "28514338226309@lid": "Teresa",
    "7001149051023@lid": "Meu numero:",
    "120363400107945602@g.us": "Balcão de Informações",
    "120363418811276924@g.us": "Gaspar Empregos !",
    "86324799369317@lid": "Levi Gatão",
    "212223360258237@lid": "Mãe",
    "125203162075156@lid": "Meu Numero Vivo",
    "180062846501005@lid": "Gleice Novo",
    "34634955775-1595618789@g.us": "LordsMobile Dark Valhalla",
    "256173492142313@lid": "Desconhecido",
    "120363417400342558@g.us": "Trip Angle 9",
    "276273888764042@lid": "Alessandra Diego Ecommerce",
    "178189703839815@lid": "Eliezer",
    "120363407425853986@g.us": "HOMENS FORJADOS 💪🏽📖🗡️🧔♂️",
    "120363107394203838@g.us": "Papo de Mulheres - IMPAC",
    "120363397899897046@g.us": "GASPAR - VENDAS , APT PARA ALUGAR",
    "120363135547556173@g.us": "GASPAR E REGIÃO 🇧🇷",
    "120363424572550633@g.us": "Padaria k80",
    "123978559537397@lid": "Jucineide Castro",
    "120363359180966787@g.us": "Açougue 80",
    "164003712131226@lid": "Yanetzi",
}

logger = logging.getLogger("n8n_service")

# Stateful mock database for in-memory development fallback
MOCK_LEADS = []
MOCK_CONVERSATIONS = {}
MOCK_ACTIVITIES = {}


class SecurityTenantMismatchError(ValueError):
    """
    Exceção de segurança disparada quando o n8n ou webhook externo retorna dados com tenant_id divergente do esperado.
    """
    pass


def validate_response_tenant(received_tenant: Optional[str], expected_tenant: Optional[str], entity_type: str = "item") -> None:
    """
    Valida estritamente se o tenant retornado pelo n8n / serviço externo corresponde ao esperado.
    Se o payload retornado contiver tenant_id e este diferir de expected_tenant:
    Registra SECURITY_TENANT_MISMATCH e levanta SecurityTenantMismatchError (fail-closed).
    """
    if received_tenant is not None and expected_tenant is not None:
        rec = str(received_tenant).strip()
        exp = str(expected_tenant).strip()
        if rec and exp and rec != exp:
            logger.error(f"SECURITY_TENANT_MISMATCH: {entity_type} returned tenant '{rec}' does not match expected tenant '{exp}'")
            raise SecurityTenantMismatchError(f"SECURITY_TENANT_MISMATCH: {entity_type} returned tenant '{rec}' does not match expected tenant '{exp}'")


def safe_parse_json(val: Any) -> dict:
    """
    Função/Método safe_parse_json.

    O que faz: Processa safe_parse_json recebendo os parâmetros (val) no contexto de o serviço de domínio n8n_service.
    Impacto na regra de negócio: Assegura que o fluxo da operação safe_parse_json seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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

def map_n8n_lead(lead: dict, conversations_map: dict = None, tenant_id: Optional[str] = None) -> dict:
    """
    Mapeia os dados do Lead provenientes do webhook N8N para a estrutura do sistema Dominus.
    Regra de Negócio: Mapeia um lead raw para garantir a consistência das entidades para o Frontend CRM e evitar dados corrompidos.
    """
    if not isinstance(lead, dict):
        return {}

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

    received_tenant = lead.get("tenant_id")
    if received_tenant and tenant_id:
        validate_response_tenant(received_tenant, tenant_id, entity_type=f"Lead {lead_id}")

    resolved_tenant = tenant_id or received_tenant
    if lead_id and lead_id.lower() != "none" and lead_id != "":
        if resolved_tenant:
            cache_k = f"{resolved_tenant}:{lead_id}"
            RAW_LEADS_CACHE[cache_k] = copy.deepcopy(lead)
            if c_jid and c_jid != lead_id:
                RAW_LEADS_CACHE[f"{resolved_tenant}:{c_jid}"] = copy.deepcopy(lead)

    raw_payload = lead.get("payload")
    payload_dict = safe_parse_json(raw_payload) if isinstance(raw_payload, str) else (raw_payload or {})
    if not isinstance(payload_dict, dict):
        payload_dict = {}

    person_name = ""

    # 1. Lookup in KNOWN_CONTACT_NAMES first
    c_jid_lookup = str(lead.get("contact_jid") or lead.get("jid") or lead.get("id") or "").strip()
    if c_jid_lookup in KNOWN_CONTACT_NAMES:
        person_name = KNOWN_CONTACT_NAMES[c_jid_lookup]
    else:
        for k, v in KNOWN_CONTACT_NAMES.items():
            if k in c_jid_lookup or c_jid_lookup in k:
                person_name = v
                break

    # 2. Check explicitly provided push_name/nome fields if not a raw JID
    if not person_name:
        for name_key in ("push_name", "nome", "nome_empresa", "empresa_nome", "company_name"):
            val = lead.get(name_key)
            if val and isinstance(val, str) and val.strip():
                v_clean = val.strip()
                v_lower = v_clean.lower()
                if v_lower not in ("desconhecido", "unknown", "null", "none") and "@lid" not in v_lower and "@s.whatsapp.net" not in v_lower and "@g.us" not in v_lower:
                    person_name = v_clean
                    break

    # 3. Use display_phone if present
    if not person_name:
        raw_phone = lead.get("display_phone") or lead.get("whatsapp") or lead.get("telefone_contato") or lead.get("phone")
        if raw_phone and isinstance(raw_phone, str) and raw_phone.strip() and raw_phone.strip().lower() not in ("null", "none") and raw_phone.strip() != "Grupo WhatsApp":
            person_name = raw_phone.strip()

    # 4. Fallback formatted name for JID
    if not person_name:
        raw_jid = lead.get("contact_jid") or lead.get("jid") or lead.get("id")
        if raw_jid and isinstance(raw_jid, str) and raw_jid.strip() and raw_jid.strip().lower() not in ("null", "none"):
            if "@g.us" in raw_jid:
                person_name = f"Grupo WhatsApp"
            elif "@lid" in raw_jid or "@s.whatsapp.net" in raw_jid:
                clean_num = "".join(filter(str.isdigit, raw_jid))
                person_name = f"Contato +{clean_num[:12]}" if len(clean_num) > 6 else "Contato WhatsApp"
            else:
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

    conv_k = f"{resolved_tenant}:{lead_id}" if resolved_tenant else None
    has_messages = False
    if conv_k and conv_k in MOCK_CONVERSATIONS and len(MOCK_CONVERSATIONS[conv_k]) > 0:
        has_messages = True
    elif conversations_map and lead_id in conversations_map and len(conversations_map[lead_id]) > 0:
        has_messages = True
    elif lead.get("has_messages") is True or lead.get("has_messages") == "true":
        has_messages = True

    mensagem_enviada = False
    if conv_k and conv_k in MOCK_CONVERSATIONS:
        if any(m.get("sender") == "user" for m in MOCK_CONVERSATIONS[conv_k]):
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
        profile_pic = f"https://dominuslabs.online{profile_pic}"

    mapped_lead = {
        **lead,
        "id": lead_id,
        "tenant_id": resolved_tenant,
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
    """
    Função/Método clean_n8n_response.

    O que faz: Processa clean_n8n_response recebendo os parâmetros (res_data) no contexto de o serviço de domínio n8n_service.
    Impacto na regra de negócio: Assegura que o fluxo da operação clean_n8n_response seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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
    """
    Função/Método extract_text_content.

    O que faz: Processa extract_text_content recebendo os parâmetros (m) no contexto de o serviço de domínio n8n_service.
    Impacto na regra de negócio: Assegura que o fluxo da operação extract_text_content seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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

def map_n8n_message(msg: dict, lead_channel: str = "whatsapp", tenant_id: Optional[str] = None) -> List[dict]:
    """
    Mapeia mensagens individuais ou aninhadas do n8n para a estrutura do Dominus com validação estrita de tenant.
    """
    if not isinstance(msg, dict):
        return []

    received_tenant = msg.get("tenant_id")
    if received_tenant and tenant_id:
        validate_response_tenant(received_tenant, tenant_id, entity_type="Message payload")

    resolved_tenant = tenant_id or received_tenant

    # 1. Support nested "mensagens" array format from n8n chat history payload
    if "mensagens" in msg and isinstance(msg["mensagens"], list):
        session_id = msg.get("session_id")
        contact_jid = msg.get("contact_jid")
        push_name = msg.get("push_name")
        display_phone = msg.get("display_phone")
        parent_is_from_me = msg.get("is_from_me") if msg.get("is_from_me") is not None else msg.get("from_me") if msg.get("from_me") is not None else msg.get("fromMe", False)
        
        profile_pic_url = msg.get("profile_pic_url") or ""
        if profile_pic_url and profile_pic_url.startswith("/"):
            profile_pic_url = f"https://dominuslabs.online{profile_pic_url}"
        mapped = []
        for m in msg["mensagens"]:
            if not isinstance(m, dict):
                continue
            m_tenant = m.get("tenant_id")
            if m_tenant and tenant_id:
                validate_response_tenant(m_tenant, tenant_id, entity_type=f"Nested message {m.get('message_id') or m.get('id')}")

            msg_id = str(m.get("message_id") or m.get("id") or "")
            is_from_me = m.get("is_from_me") if m.get("is_from_me") is not None else m.get("from_me") if m.get("from_me") is not None else m.get("fromMe", parent_is_from_me)
            sender = "user" if is_from_me else "lead"
            direction = "outgoing" if is_from_me else "incoming"

            raw_text = extract_text_content(m)
            raw_media = m.get("media_url") or m.get("image_url") or m.get("url") or m.get("file_url") or m.get("image") or None

            ts = m.get("message_timestamp") or m.get("created_at") or m.get("timestamp") or m.get("createdAt") or msg.get("created_at")

            mapped.append({
                "id": msg_id,
                "message_id": msg_id,
                "session_id": m.get("session_id") or session_id,
                "tenant_id": tenant_id or m_tenant or resolved_tenant,
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
                "image_url": raw_media,
                "media_url": raw_media,
                "push_name": m.get("push_name") or push_name,
                "participant_pushname": m.get("participant_pushname") or m.get("participant_push_name") or m.get("participant_name") or msg.get("participant_pushname"),
                "participant": m.get("participant") or m.get("participant_jid") or msg.get("participant"),
                "display_phone": display_phone,
                "profile_pic_url": profile_pic_url,
                "channel": lead_channel,
                "timestamp": ts,
                "status": m.get("status") or msg.get("status", "received"),
                "quoted_message_id": m.get("quoted_message_id") or m.get("quoted_id") or m.get("quotedId") or None,
                "quoted_participant": m.get("quoted_participant") or m.get("quoted_sender") or m.get("quotedParticipant") or None,
                "quoted_text": m.get("quoted_text") or m.get("quoted_content") or m.get("quotedText") or None,
                "reaction_text": m.get("reaction_text") or m.get("reactionText") or None,
                "reaction_target_message_id": m.get("reaction_target_message_id") or m.get("reactionTargetMessageId") or None,
                "reaction_target_sender_jid": m.get("reaction_target_sender_jid") or m.get("reactionTargetSenderJid") or None,
            })
        return mapped

    # 2. Support direct whats-api / n8n single incoming message object
    if "is_from_me" in msg or "message_id" in msg or "contact_jid" in msg or "push_name" in msg or "session_id" in msg or "content" in msg or "chat_kind" in msg:
        msg_id = str(msg.get("message_id") or msg.get("id") or "")
        is_from_me = msg.get("is_from_me") if msg.get("is_from_me") is not None else msg.get("from_me") if msg.get("from_me") is not None else msg.get("fromMe", False)
        sender = "user" if is_from_me else "lead"
        direction = "outgoing" if is_from_me else "incoming"
        
        raw_text = extract_text_content(msg)
        raw_media = msg.get("media_url") or msg.get("image_url") or msg.get("url") or msg.get("file_url") or msg.get("image") or None
        profile_pic_url = msg.get("profile_pic_url") or ""
        if profile_pic_url and profile_pic_url.startswith("/"):
            profile_pic_url = f"https://dominuslabs.online{profile_pic_url}"

        ts = msg.get("message_timestamp") or msg.get("created_at") or msg.get("timestamp") or msg.get("createdAt")

        mapped = [{
            "id": msg_id,
            "message_id": msg_id,
            "session_id": msg.get("session_id"),
            "tenant_id": resolved_tenant,
            "contact_jid": msg.get("contact_jid") or msg.get("jid"),
            "is_from_me": is_from_me,
            "sender": sender,
            "direction": direction,
            "sent_by_user": is_from_me,
            "message": raw_text,
            "content": raw_text,
            "caption": msg.get("caption", ""),
            "message_type": msg.get("message_type") or msg.get("type") or "conversation",
            "chat_kind": msg.get("chat_kind", "private"),
            "image_url": raw_media,
            "media_url": raw_media,
            "push_name": msg.get("push_name") or msg.get("participant_pushname"),
            "participant_pushname": msg.get("participant_pushname") or msg.get("participant_push_name") or msg.get("participant_name") or msg.get("push_name"),
            "participant": msg.get("participant") or msg.get("participant_jid"),
            "display_phone": msg.get("display_phone"),
            "profile_pic_url": profile_pic_url,
            "channel": lead_channel,
            "timestamp": ts,
            "message_timestamp": ts,
            "created_at": msg.get("created_at") or ts,
            "status": msg.get("status", "received"),
            "quoted_message_id": msg.get("quoted_message_id") or msg.get("quoted_id") or msg.get("quotedId") or None,
            "quoted_participant": msg.get("quoted_participant") or msg.get("quoted_sender") or msg.get("quotedParticipant") or None,
            "quoted_text": msg.get("quoted_text") or msg.get("quoted_content") or msg.get("quotedText") or None,
            "reaction_text": msg.get("reaction_text") or msg.get("reactionText") or None,
            "reaction_target_message_id": msg.get("reaction_target_message_id") or msg.get("reactionTargetMessageId") or None,
            "reaction_target_sender_jid": msg.get("reaction_target_sender_jid") or msg.get("reactionTargetSenderJid") or None,
        }]
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
        """
        Função/Método update_keys.

        O que faz: Atualização e modificação de informações para update_keys recebendo os parâmetros (d, mappings) no contexto de o serviço de domínio n8n_service.
        Impacto na regra de negócio: Assegura que o fluxo da operação update_keys seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
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
    top_mappings["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    top_mappings["updatedAt"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"

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
    """
    Função/Método normalize_session_name.

    O que faz: Processa normalize_session_name recebendo os parâmetros (name) no contexto de o serviço de domínio n8n_service.
    Impacto na regra de negócio: Assegura que o fluxo da operação normalize_session_name seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    if not name:
        return ""
    return name.lower().replace("-", "").replace("_", "").replace(" ", "")

def unpack_n8n_raw_leads(raw_leads: List[dict]) -> List[dict]:
    """
    Função/Método unpack_n8n_raw_leads.

    O que faz: Processa unpack_n8n_raw_leads recebendo os parâmetros (raw_leads) no contexto de o serviço de domínio n8n_service.
    Impacto na regra de negócio: Assegura que o fluxo da operação unpack_n8n_raw_leads seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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
                    c_copy["profile_pic_url"] = f"https://dominuslabs.online{pic}"

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
                    c_copy["profile_pic_url"] = f"https://dominuslabs.online{pic}"

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
                        profile_pic = f"https://dominuslabs.online{profile_pic}"

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
                        pic = f"https://dominuslabs.online{pic}"
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
                            m_pic = f"https://dominuslabs.online{m_pic}"
                        item_copy["profile_pic_url"] = str(m_pic)
            if c_jid and s_id and s_id != "default":
                group_key = f"{c_jid}___{s_id}"
                item_copy["id"] = group_key
                item_copy["lead_id"] = group_key
            unpacked.append(item_copy)

    return unpacked

class ProgressiveContactCache:
    """
    Thread-safe in-memory progressive cache isolado por (tenant_id, contact_jid).
    Mantém o estado do perfil através das etapas do CRM sem vazamento entre tenants.
    """
    _cache: Dict[str, dict] = {}

    @classmethod
    def _cache_key(cls, jid: str, tenant_id: Optional[str] = None) -> str:
        if not jid:
            return ""
        return f"{tenant_id}::{jid}" if tenant_id else str(jid)

    @classmethod
    def get(cls, jid: str, tenant_id: Optional[str] = None) -> Optional[dict]:
        if not jid:
            return None
        return cls._cache.get(cls._cache_key(jid, tenant_id))

    @classmethod
    def set_contact(cls, jid: str, contact_data: dict, tenant_id: Optional[str] = None) -> dict:
        if not jid:
            return contact_data
        effective_tenant = tenant_id or contact_data.get("tenant_id")
        key = cls._cache_key(jid, effective_tenant)
        existing = cls._cache.get(key, {})
        existing.update({
            "contact_jid": jid,
            "tenant_id": effective_tenant,
            "push_name": contact_data.get("push_name") or existing.get("push_name") or "Contato Sem Nome",
            "profile_pic_url": contact_data.get("profile_pic_url") or existing.get("profile_pic_url") or "",
            "display_phone": contact_data.get("display_phone") or existing.get("display_phone") or "",
            "whatsapp": contact_data.get("whatsapp") or existing.get("whatsapp") or "",
            "email": contact_data.get("email") or existing.get("email") or "",
            "status": contact_data.get("status") or existing.get("status") or "Prospectado",
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        })
        for k in ("session_id", "unread_count", "last_message_preview", "mensagens", "messages"):
            if k in contact_data:
                existing[k] = contact_data[k]
        cls._cache[key] = existing
        return existing

    @classmethod
    def set_conversation(cls, jid: str, conv_data: dict, tenant_id: Optional[str] = None) -> dict:
        if not jid:
            return conv_data
        effective_tenant = tenant_id or conv_data.get("tenant_id")
        key = cls._cache_key(jid, effective_tenant)
        existing = cls._cache.get(key, {"contact_jid": jid, "tenant_id": effective_tenant})
        existing["session_id"] = conv_data.get("session_id") or existing.get("session_id", "default")
        existing["unread_count"] = conv_data.get("unread_count", 0)
        existing["last_message_preview"] = conv_data.get("last_message_preview") or conv_data.get("content", "")
        if conv_data.get("push_name") and conv_data.get("push_name") not in ("Desconhecido", "Contato Sem Nome"):
            existing["push_name"] = conv_data["push_name"]
        if conv_data.get("profile_pic_url"):
            existing["profile_pic_url"] = conv_data["profile_pic_url"]
        existing["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        cls._cache[key] = existing
        return existing

    @classmethod
    def set_messages(cls, jid: str, messages_list: List[dict], tenant_id: Optional[str] = None) -> dict:
        if not jid:
            return {}
        key = cls._cache_key(jid, tenant_id)
        existing = cls._cache.get(key, {"contact_jid": jid, "tenant_id": tenant_id})
        existing["mensagens"] = messages_list
        existing["messages"] = messages_list
        existing["has_messages"] = len(messages_list) > 0
        existing["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        cls._cache[key] = existing
        return existing

    @classmethod
    def get_assembled_payload(cls, jid: str, tenant_id: Optional[str] = None) -> dict:
        key = cls._cache_key(jid, tenant_id)
        return cls._cache.get(key, {"contact_jid": jid, "tenant_id": tenant_id, "mensagens": []})

    @classmethod
    def clear(cls, tenant_id: Optional[str] = None):
        if tenant_id:
            keys_to_del = [k for k in cls._cache if k.startswith(f"{tenant_id}::")]
            for k in keys_to_del:
                cls._cache.pop(k, None)
        else:
            cls._cache.clear()

class N8NService:
    """
    Classe N8NService.

    O que faz: Representa a estrutura de dados e operações para a entidade N8NService em o serviço de domínio n8n_service.
    Impacto na regra de negócio: Centraliza o comportamento da entidade N8NService, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    # Leads cache state particionado por tenant_id
    _leads_cache: Dict[str, dict] = {}
    CACHE_TTL = 10.0  # seconds

    @staticmethod
    def _enrich_payload(base_payload: dict, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> dict:
        """
        Enriquece o payload com tenant_id e user_id em modo fail-closed (sem fallback para admin).
        """
        p = dict(base_payload)
        resolved_tenant = tenant_id or p.get("tenant_id")
        if not resolved_tenant:
            logger.error("[Zero-Trust] Falha de isolamento multi-tenant: tenant_id é obrigatório para enrich_payload")
            raise ValueError("[Zero-Trust] Falha de isolamento multi-tenant: tenant_id é obrigatório para enrich_payload")
        resolved_user = user_id or p.get("user_id") or p.get("alterado_por") or p.get("updated_by") or "system"
        p["tenant_id"] = resolved_tenant
        p["user_id"] = resolved_user
        p["alterado_por"] = resolved_user
        p["updated_by"] = resolved_user
        return p

    @staticmethod
    def invalidate_leads_cache(tenant_id: Optional[str] = None):
        """
        Invalida o cache de leads de um tenant específico ou de todos os tenants.
        """
        if tenant_id:
            N8NService._leads_cache.pop(tenant_id, None)
            logger.info(f"CRM Leads Cache explicitly invalidated for tenant_id={tenant_id}.")
        else:
            N8NService._leads_cache.clear()
            logger.info("CRM Leads Cache explicitly invalidated for all tenants.")

    @staticmethod
    async def run_scrapper(payload: dict, platform: str = "meta_ads", user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> dict:
        """
        Função/Método run_scrapper.
        """
        fallback_url = settings.SCRAPPER_META_WEBHOOK_URL if platform == "meta_ads" else settings.SCRAPPER_MAPS_WEBHOOK_URL
        url = payload.get("webhook_url") or fallback_url
        if not url:
            logger.info("SCRAPPER Webhook URL not configured. Returning mock success.")
            return {"status": "success", "message": "Scrapper triggered (MOCK Mode)", "data": payload}

        outgoing_payload = {
            "action": "run_scrapper",
            "queries": payload.get("queries", []),
            "min_results": payload.get("min_results", 10),
            "max_results": payload.get("max_results", 20),
        }
        if "target_platform" in payload and payload["target_platform"]:
            outgoing_payload["target_platform"] = payload["target_platform"]
            if payload["target_platform"] in ("whatsapp", "instagram"):
                outgoing_payload["contact_channel"] = payload["target_platform"]
        if "contact_channel" in payload and payload["contact_channel"]:
            outgoing_payload["contact_channel"] = payload["contact_channel"]
        if "objective" in payload and payload["objective"]:
            outgoing_payload["objective"] = payload["objective"]

        outgoing_payload = N8NService._enrich_payload(outgoing_payload, user_id=user_id or payload.get("user_id"), tenant_id=tenant_id or payload.get("tenant_id"))
        encrypted_payload = encrypt_payload(outgoing_payload, "n8n")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(url, json=encrypted_payload, timeout=30.0)
                response.raise_for_status()
                res_data = response.json()
                if isinstance(res_data, dict) and res_data.get("_encrypted") is True:
                    res_data = decrypt_payload(res_data)
                return clean_n8n_response(res_data)
            except Exception as e:
                logger.error(f"Error calling Scrapper webhook: {e}")
                return {"status": "error", "message": str(e)}

    @staticmethod
    async def get_leads(user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> List[dict]:
        """
        Recuperação de leads isolada estritamente por tenant_id.
        """
        if not tenant_id:
            logger.error("[Zero-Trust] get_leads chamado sem tenant_id!")
            raise ValueError("[Zero-Trust] tenant_id é obrigatório para get_leads")

        url = settings.CRM_GET_LEADS_WEBHOOK_URL
        # Check tenant-specific cache
        tenant_cache = N8NService._leads_cache.get(tenant_id)
        if tenant_cache is not None:
            if time.time() - tenant_cache.get("time", 0.0) < N8NService.CACHE_TTL:
                if tenant_cache.get("url") == url:
                    logger.info(f"Returning CRM Leads from in-memory cache for tenant_id={tenant_id}.")
                    return tenant_cache.get("data", [])

        if not url:
            logger.info("CRM_GET_LEADS_WEBHOOK_URL not configured. Returning mock leads.")
            mapped_mock = [map_n8n_lead(l, tenant_id=tenant_id) for l in MOCK_LEADS if l.get("tenant_id") == tenant_id]
            mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
            mapped_mock.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
            N8NService._leads_cache[tenant_id] = {
                "data": mapped_mock,
                "time": time.time(),
                "url": url
            }
            return mapped_mock

        outgoing_body = N8NService._enrich_payload({"action": "get_contacts"}, user_id=user_id, tenant_id=tenant_id)
        encrypted_body = encrypt_payload(outgoing_body, "n8n")
        raw_leads = None
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(url, json=encrypted_body, timeout=30.0)
                if response.status_code >= 400:
                    logger.warning(f"[N8N-STEALTH] POST request to {url} returned status {response.status_code}. Ensure the n8n Webhook node HTTP Method is set to POST.")
                response.raise_for_status()
                data = response.json()
                data = decrypt_payload(data)
                if isinstance(data, list):
                    raw_leads = data
                elif isinstance(data, dict) and "leads" in data:
                    raw_leads = data["leads"]
                elif isinstance(data, dict) and "mensagens" in data:
                    raw_leads = [data]
            except Exception as e:
                logger.error(f"Error calling POST leads webhook: {e}. Falling back to mock data.", exc_info=True)
        if not raw_leads:
            mapped_mock = [map_n8n_lead(l, tenant_id=tenant_id) for l in MOCK_LEADS if l.get("tenant_id") == tenant_id]
            mapped_mock.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
            mapped_mock.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
            for m in mapped_mock:
                c_jid = m.get("contact_jid") or m.get("jid") or m.get("id")
                if c_jid:
                    ProgressiveContactCache.set_contact(c_jid, m, tenant_id=tenant_id)
            N8NService._leads_cache[tenant_id] = {
                "data": mapped_mock,
                "time": time.time(),
                "url": url
            }
            return mapped_mock

        raw_leads = unpack_n8n_raw_leads(raw_leads)
        mapped_leads = []
        for l in raw_leads:
            if not isinstance(l, dict):
                continue
            l_tenant = l.get("tenant_id")
            if l_tenant and tenant_id and str(l_tenant).strip() != str(tenant_id).strip():
                logger.error(f"SECURITY_TENANT_MISMATCH: Dropping lead {l.get('id')} from tenant '{l_tenant}' (expected '{tenant_id}')")
                continue
            try:
                mapped_leads.append(map_n8n_lead(l, tenant_id=tenant_id))
            except SecurityTenantMismatchError as e:
                logger.error(f"SECURITY_TENANT_MISMATCH caught during get_leads: {e}")
                continue

        mapped_leads.sort(key=lambda x: x.get("last_interaction") or "", reverse=True)
        mapped_leads.sort(key=lambda x: x.get("mensagem_enviada", False), reverse=True)
        
        # Step 1: Cache basic info by contact_jid scoped by tenant
        for m in mapped_leads:
            c_jid = m.get("contact_jid") or m.get("jid") or m.get("id")
            if c_jid:
                ProgressiveContactCache.set_contact(c_jid, m, tenant_id=tenant_id)

        N8NService._leads_cache[tenant_id] = {
            "data": mapped_leads,
            "time": time.time(),
            "url": url
        }
        return mapped_leads

    @staticmethod
    async def get_conversations(user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> List[dict]:
        """
        Obtém a lista de conversas ativas via action=get_conversations no webhook CRM com Zero-Trust.
        """
        if not tenant_id:
            logger.error("[Zero-Trust] get_conversations chamado sem tenant_id!")
            raise ValueError("[Zero-Trust] tenant_id é obrigatório para get_conversations")

        url = settings.CRM_GET_MESSAGES_WEBHOOK_URL or settings.CRM_GET_LEADS_WEBHOOK_URL
        if not url:
            return []

        outgoing_body = N8NService._enrich_payload({"action": "get_conversations"}, user_id=user_id, tenant_id=tenant_id)
        encrypted_body = encrypt_payload(outgoing_body, "n8n")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(url, json=encrypted_body, timeout=30.0)
                if response.status_code >= 400:
                    logger.warning(f"[N8N-STEALTH] POST request to {url} returned status {response.status_code}. Ensure the n8n Webhook node HTTP Method is set to POST.")
                response.raise_for_status()
                data = response.json()
                data = decrypt_payload(data)

                raw_convs = []
                if isinstance(data, list):
                    raw_convs = data
                elif isinstance(data, dict):
                    raw_convs = data.get("conversas") or data.get("conversations") or data.get("leads") or [data]
                
                unpacked = unpack_n8n_raw_leads(raw_convs)
                mapped = []
                for l in unpacked:
                    if not isinstance(l, dict):
                        continue
                    l_tenant = l.get("tenant_id")
                    if l_tenant and tenant_id and str(l_tenant).strip() != str(tenant_id).strip():
                        logger.error(f"SECURITY_TENANT_MISMATCH: Dropping conversation {l.get('id')} from tenant '{l_tenant}' (expected '{tenant_id}')")
                        continue
                    try:
                        mapped.append(map_n8n_lead(l, tenant_id=tenant_id))
                    except SecurityTenantMismatchError as e:
                        logger.error(f"SECURITY_TENANT_MISMATCH caught during get_conversations: {e}")
                        continue
                
                # Step 2: Append conversation inbox state to cached contact profile & compute last_message_preview
                for m in mapped:
                    if not m.get("last_message_preview"):
                        msgs = m.get("mensagens") or m.get("messages") or []
                        if isinstance(msgs, list) and len(msgs) > 0:
                            last_msg = msgs[0] if isinstance(msgs[0], dict) else {}
                            m["last_message_preview"] = extract_text_content(last_msg) or last_msg.get("content") or last_msg.get("message") or ""
                            if not m.get("last_message_timestamp") and last_msg.get("message_timestamp"):
                                m["last_message_timestamp"] = last_msg["message_timestamp"]
                    c_jid = m.get("contact_jid") or m.get("jid") or m.get("id")
                    if c_jid:
                        ProgressiveContactCache.set_conversation(c_jid, m, tenant_id=tenant_id)

                # Sort conversations descending (newest last_message_timestamp first)
                mapped.sort(
                    key=lambda x: str(x.get("last_message_timestamp") or x.get("updated_at") or x.get("last_interaction") or ""),
                    reverse=True
                )

                return mapped
            except Exception as e:
                logger.error(f"Error calling POST conversations webhook: {e}")
                return []

    @staticmethod
    async def get_chat_history(lead_id: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> List[dict]:
        """
        Alias para get_messages utilizando action=get_chat_history.
        """
        return await N8NService.get_messages(lead_id, user_id=user_id, tenant_id=tenant_id)

    @staticmethod
    async def update_lead(lead_id: str, payload: dict, current_user: Optional[str] = None, tenant_id: Optional[str] = None) -> dict:
        """
        Atualização de lead com Zero-Trust e isolamento estrito por tenant_id.
        """
        N8NService.invalidate_leads_cache(tenant_id=tenant_id)
        url = settings.CRM_UPDATE_LEAD_WEBHOOK_URL

        cache_k = f"{tenant_id}:{lead_id}" if tenant_id else str(lead_id)
        # Try to find in cache strictly partitioned by tenant
        raw_lead = None
        if cache_k in RAW_LEADS_CACHE:
            raw_lead = copy.deepcopy(RAW_LEADS_CACHE[cache_k])

        if not raw_lead:
            # Fallback template with Portuguese keys if not in cache
            raw_lead = {
                "lead_id": lead_id,
                "tenant_id": tenant_id,
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
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
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
        RAW_LEADS_CACHE[cache_k] = copy.deepcopy(outgoing_payload)

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
            if lead["id"] == lead_id and lead.get("tenant_id") == tenant_id:
                for k, v in payload.items():
                    lead[k] = v
                lead["payload"] = reconstructed_payload_meta
                lead["presenca_digital"] = reconstructed_presenca
                lead["reputacao_google"] = reconstructed_reputacao
                lead["oportunidades_identificadas"] = reconstructed_oportunidades
                lead["last_interaction"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
                if current_user:
                    lead["alterado_por"] = current_user
                    lead["updated_by"] = current_user
                MOCK_LEADS[i] = lead
                break
        if not url:
            logger.info("CRM_UPDATE_LEAD_WEBHOOK_URL not configured. Lead updated locally in-memory.")
            updated_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id and l.get("tenant_id") == tenant_id), None)
            mapped = map_n8n_lead(updated_lead, tenant_id=tenant_id) if updated_lead else map_n8n_lead({"id": lead_id, **payload, "tenant_id": tenant_id}, tenant_id=tenant_id)
            if current_user:
                mapped["alterado_por"] = current_user
                mapped["updated_by"] = current_user
            return mapped

        # Encrypt action, lead_id, user_id and tenant_id inside payload for Zero-Trust stealth
        outgoing_payload["action"] = "update_lead"
        outgoing_payload["id"] = lead_id
        outgoing_payload["lead_id"] = lead_id
        outgoing_payload = N8NService._enrich_payload(outgoing_payload, user_id=current_user, tenant_id=tenant_id)
        encrypted_payload = encrypt_payload(outgoing_payload, "n8n")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                # Tenta POST com payload 100% criptografado (Zero-Trust fail-closed sem fallback plaintext)
                response = await client.post(url, json=encrypted_payload, timeout=30.0)
                response.raise_for_status()
                res_data = clean_n8n_response(response.json())
                if isinstance(res_data, dict) and res_data.get("_encrypted") is True:
                    res_data = decrypt_payload(res_data)
                if isinstance(res_data, dict) and ("company_name" in res_data or "nome_empresa" in res_data or "empresa_nome" in res_data):
                    mapped = map_n8n_lead(res_data, tenant_id=tenant_id)
                else:
                    fallback_lead = next((l for l in MOCK_LEADS if l["id"] == lead_id and l.get("tenant_id") == tenant_id), None)
                    if fallback_lead:
                        mapped = map_n8n_lead(fallback_lead, tenant_id=tenant_id)
                    else:
                        mapped = map_n8n_lead({"id": lead_id, **payload, "tenant_id": tenant_id}, tenant_id=tenant_id)
                if current_user:
                    mapped["alterado_por"] = current_user
                    mapped["updated_by"] = current_user
                return mapped
            except Exception as e:
                logger.error(f"Error calling UPDATE lead webhook: {e}")
                raise e

    @staticmethod
    async def delete_lead(lead_id: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> dict:
        """
        Remoção segura e exclusão lógica/física para delete_lead em modo Zero-Trust fail-closed.
        """
        N8NService.invalidate_leads_cache(tenant_id=tenant_id)
        url = settings.CRM_UPDATE_LEAD_WEBHOOK_URL

        # Remove from mock lists strictly partitioned by tenant
        for i, lead in enumerate(MOCK_LEADS):
            if str(lead.get("id")) == str(lead_id) and (not tenant_id or lead.get("tenant_id") == tenant_id):
                MOCK_LEADS.pop(i)
                break
        cache_k = f"{tenant_id}:{lead_id}" if tenant_id else str(lead_id)
        RAW_LEADS_CACHE.pop(cache_k, None)
        MOCK_CONVERSATIONS.pop(cache_k, None)
        MOCK_ACTIVITIES.pop(cache_k, None)

        if not url:
            logger.info("CRM_UPDATE_LEAD_WEBHOOK_URL not configured. Lead deleted locally in-memory.")
            return {"status": "success", "message": "Lead deleted locally (MOCK Mode)", "id": lead_id}

        outgoing_body = N8NService._enrich_payload({"action": "delete_lead", "id": lead_id, "lead_id": lead_id}, user_id=user_id, tenant_id=tenant_id)
        encrypted_payload = encrypt_payload(outgoing_body, "n8n")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                # Tenta POST com payload 100% criptografado (Zero-Trust fail-closed sem fallback plaintext)
                response = await client.post(url, json=encrypted_payload, timeout=30.0)
                response.raise_for_status()
                try:
                    res_data = clean_n8n_response(response.json())
                    if isinstance(res_data, dict) and res_data.get("_encrypted") is True:
                        res_data = decrypt_payload(res_data)
                    if isinstance(res_data, dict):
                        return res_data
                except Exception:
                    pass
                return {"status": "success", "id": lead_id}
            except Exception as e:
                logger.error(f"Error calling DELETE lead webhook: {e}")
                raise e

    @staticmethod
    async def get_messages(lead_id: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> List[dict]:
        """
        Função/Método get_messages.

        O que faz: Recuperação de dados cadastrados para get_messages recebendo os parâmetros (lead_id, user_id, tenant_id) no contexto de o serviço de domínio n8n_service.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_messages seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        cache_k = f"{tenant_id}:{lead_id}" if tenant_id else str(lead_id)
        all_msgs = list(MOCK_CONVERSATIONS.get(cache_k, []))
        url = settings.CRM_GET_MESSAGES_WEBHOOK_URL

        target_id_str = str(lead_id).strip()
        target_jid = target_id_str
        target_session = None
        if "___" in target_id_str:
            parts = target_id_str.split("___", 1)
            target_jid = parts[0]
            target_session = parts[1]

        cached_lead = RAW_LEADS_CACHE.get(cache_k)
        if not cached_lead:
            cached_lead = RAW_LEADS_CACHE.get(f"{tenant_id}:{target_jid}" if tenant_id else target_jid)
        if cached_lead and "mensagens" in cached_lead and isinstance(cached_lead["mensagens"], list):
            embedded_msgs = []
            seen_keys = set()
            lead_channel = cached_lead.get("origin", "whatsapp").lower()
            for m in cached_lead["mensagens"]:
                if not isinstance(m, dict):
                    continue
                try:
                    mapped_list = map_n8n_message(m, lead_channel, tenant_id=tenant_id)
                except SecurityTenantMismatchError as e:
                    logger.error(f"SECURITY_TENANT_MISMATCH caught during embedded cached messages: {e}")
                    continue
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
                MOCK_CONVERSATIONS[cache_k] = embedded_msgs
        if not url:
            return MOCK_CONVERSATIONS.get(cache_k, all_msgs)

        lid = None
        if cached_lead:
            lid = cached_lead.get("lid") or cached_lead.get("LID") or cached_lead.get("Lid")

        outgoing_body = {
            "action": "get_chat_history",
            "lead_id": target_jid,
            "contact_jid": target_jid,
            "session_id": target_session
        }
        if lid:
            outgoing_body["lid"] = lid
        outgoing_body = N8NService._enrich_payload(outgoing_body, user_id=user_id, tenant_id=tenant_id)
        encrypted_body = encrypt_payload(outgoing_body, "n8n")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(url, json=encrypted_body, timeout=30.0)
                if response.status_code >= 400:
                    logger.warning(f"[N8N-STEALTH] POST request to {url} returned status {response.status_code}. Ensure the n8n Webhook node HTTP Method is set to POST.")
                response.raise_for_status()
                body = response.text.strip()
                raw_msgs = []
                if body:
                    data = response.json()
                    data = decrypt_payload(data)
                    if isinstance(data, list):
                        for d in data:
                            if isinstance(d, dict):
                                d_sess = str(d.get("session_id") or d.get("whatsapp_instance") or "")
                                if target_session and d_sess and normalize_session_name(d_sess) != normalize_session_name(target_session):
                                    continue
                                if "messages" in d and isinstance(d["messages"], list):
                                    raw_msgs.extend(d["messages"])
                                elif "mensagens" in d and isinstance(d["mensagens"], list):
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
                        m_tenant = m.get("tenant_id")
                        if m_tenant and tenant_id and str(m_tenant).strip() != str(tenant_id).strip():
                            logger.error(f"SECURITY_TENANT_MISMATCH: Skipping message {m.get('id')} from tenant '{m_tenant}' (expected '{tenant_id}')")
                            continue
                        try:
                            mapped_list = map_n8n_message(m, lead_channel, tenant_id=tenant_id)
                        except SecurityTenantMismatchError as e:
                            logger.error(f"SECURITY_TENANT_MISMATCH caught during get_messages: {e}")
                            continue
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
                
                # Step 3: Append full chat history to cached contact profile scoped by tenant
                ProgressiveContactCache.set_messages(target_jid, fresh_msgs, tenant_id=tenant_id)
                if len(fresh_msgs) > 0:
                    MOCK_CONVERSATIONS[cache_k] = fresh_msgs
                    return fresh_msgs

                return MOCK_CONVERSATIONS.get(cache_k, [])
            except Exception as e:
                logger.error(f"Error calling GET messages webhook: {e}. Returning cached.")
                return MOCK_CONVERSATIONS.get(cache_k, all_msgs)

    @staticmethod
    def _extract_n8n_error_message(resp_data) -> Optional[str]:
        """
        Função/Método _extract_n8n_error_message.

        O que faz: Processa _extract_n8n_error_message recebendo os parâmetros (resp_data) no contexto de o serviço de domínio n8n_service.
        Impacto na regra de negócio: Assegura que o fluxo da operação _extract_n8n_error_message seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
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
    async def create_activity(lead_id: str, event_type: str, metadata: dict, tenant_id: Optional[str] = None) -> dict:
        """
        Criação de novos registros e processamento para create_activity isolado por tenant_id.
        """
        new_activity = {
            "lead_id": lead_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "metadata": metadata
        }
        cache_k = f"{tenant_id}:{lead_id}" if tenant_id else str(lead_id)
        if cache_k not in MOCK_ACTIVITIES:
            MOCK_ACTIVITIES[cache_k] = []
        MOCK_ACTIVITIES[cache_k].append(new_activity)
        return new_activity

    @staticmethod
    async def get_activities(lead_id: str, tenant_id: Optional[str] = None) -> List[dict]:
        """
        Recuperação de atividades cadastrados para get_activities isolado por tenant_id.
        """
        cache_k = f"{tenant_id}:{lead_id}" if tenant_id else str(lead_id)
        return MOCK_ACTIVITIES.get(cache_k, [])

n8n_service = N8NService()
