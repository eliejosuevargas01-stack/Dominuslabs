"""
Documentação do módulo crm.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para crm.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para crm funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
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
async def read_leads(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Fetch all leads from the n8n CRM webhook or fallback to direct WhatsApp API.
    """
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        leads = await n8n_service.get_leads(user_id=current_user)
# Lógica de decisão (if): Avalia 'if leads and len(leads) > 0:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if leads and len(leads) > 0:
            return leads
    except Exception as e:
        print(f"[CRM] n8n get_leads falhou: {e}", flush=True)

    from app.services.n8n_service import map_n8n_lead
    raw_contacts = await get_contacts_action(db=db, current_user=current_user)
    return [map_n8n_lead(c) for c in raw_contacts if isinstance(c, dict)]

@router.get("/leads/{lead_id}", response_model=Lead)
async def read_lead(lead_id: str, current_user: str = Depends(get_current_user)):
    """
    Fetch a single lead by its ID.
    """
    leads = await n8n_service.get_leads(user_id=current_user)
    lead = next((l for l in leads if str(l.get("id")) == str(lead_id)), None)
# Lógica de decisão (if): Avalia 'if not lead:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
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
    result = await n8n_service.delete_lead(lead_id, user_id=current_user)
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
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        leads = await n8n_service.get_leads(user_id=current_user)
        contacts = []
# Lógica de repetição (for): Itera sobre elementos de 'for l in leads:...' processando múltiplos dados em lote para as regras de domínio.
        for l in leads:
            contacts.append({
                "contact_jid": l.get("contact_jid") or l.get("jid") or l.get("id"),
                "push_name": l.get("push_name") or l.get("nome") or "Contato Sem Nome",
                "display_phone": l.get("display_phone") or l.get("whatsapp") or None,
                "profile_pic_url": l.get("profile_pic_url") or "",
                "created_at": l.get("created_at") or datetime.utcnow().isoformat() + "Z",
                "updated_at": l.get("updated_at") or datetime.utcnow().isoformat() + "Z",
                "tenant_id": l.get("tenant_id") or "admin"
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
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        convs = await n8n_service.get_conversations(user_id=current_user)
# Lógica de decisão (if): Avalia 'if convs and len(convs) > 0:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if convs and len(convs) > 0:
            return convs
    except Exception as e:
        print(f"[CRM] n8n get_conversations error: {e}", flush=True)

    # Fallback return standard leads format mapped to conversations preview
    leads = await n8n_service.get_leads(user_id=current_user)
    result = []
# Lógica de repetição (for): Itera sobre elementos de 'for l in leads:...' processando múltiplos dados em lote para as regras de domínio.
    for l in leads:
        result.append({
            "contact_jid": l.get("contact_jid") or l.get("jid") or l.get("id"),
            "push_name": l.get("push_name") or l.get("nome") or "Contato",
            "display_phone": l.get("display_phone") or l.get("whatsapp") or None,
            "profile_pic_url": l.get("profile_pic_url") or "",
            "session_id": l.get("session_id") or "default",
            "unread_count": l.get("unread_count", 0),
            "last_message_preview": l.get("last_message_preview") or l.get("ultima_mensagem") or "",
            "last_message_timestamp": l.get("last_message_timestamp") or l.get("last_interaction") or l.get("updated_at") or datetime.utcnow().isoformat() + "Z"
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
    lookup_id = f"{contact_jid}___{session_id}" if session_id and session_id != "default" else contact_jid
    return await n8n_service.get_messages(lookup_id, user_id=current_user)

from fastapi.responses import RedirectResponse, Response

@router.get("/avatar")
async def proxy_crm_avatar(
    jid: str,
    session: Optional[str] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Proxy de avatar público para ser consumido por tags <img> no Dominus CRM.
    Recebe session/session_id e jid, consulta a Whats API via rede Docker mTLS e devolve
    o redirecionamento para a CDN oficial do Meta (pps.whatsapp.net) ou a imagem.
    """
    target_session = session or session_id or "default"
# Lógica de decisão (if): Avalia 'if not jid:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not jid:
        raise HTTPException(status_code=400, detail="Parâmetro 'jid' é obrigatório.")

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        from app.api.endpoints.whatsapp import make_whatsapp_api_request
        clean_path = f"/api/sessions/{target_session}/avatar?jid={jid}&json=true"
        res = None
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            res = await make_whatsapp_api_request("GET", clean_path)
        except Exception:
            fallback_path = f"/avatar?session={target_session}&jid={jid}&json=true"
            res = await make_whatsapp_api_request("GET", fallback_path)

        url_target = None
# Lógica de decisão (if): Avalia 'if isinstance(res, dict):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if isinstance(res, dict):
            url_target = res.get("url") or res.get("avatar_url") or res.get("profile_pic_url") or res.get("profile_url") or res.get("avatar")

# Lógica de decisão (if): Avalia 'if url_target:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if url_target:
            return RedirectResponse(
                url_target,
                status_code=302,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=86400"
                }
            )
    except Exception as e:
        print(f"[CRM-AVATAR] Aviso ao buscar avatar proxy para jid={jid}: {e}", flush=True)

    raise HTTPException(status_code=404, detail="Avatar não encontrado.")

@router.get("/media")
@router.get("/sessions/{session_id}/media")
async def proxy_crm_media(
    messageId: Optional[str] = None,
    message_id: Optional[str] = None,
    session: Optional[str] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Proxy de mídia (imagens, áudios, vídeos e documentos) da WhatsApp API via mTLS para tags <img>, <video>, <audio> e <a>.
    """
    target_session = session or session_id or "default"
    target_msg_id = messageId or message_id
# Lógica de decisão (if): Avalia 'if not target_msg_id:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not target_msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        from app.api.endpoints.whatsapp import make_whatsapp_api_request
        clean_path = f"/api/sessions/{target_session}/media?messageId={target_msg_id}"
        res = await make_whatsapp_api_request("GET", clean_path, timeout=30.0)

# Lógica de decisão (if): Avalia 'if isinstance(res, dict):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if isinstance(res, dict):
# Lógica de decisão (if): Avalia 'if res.get("_is_binary"):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if res.get("_is_binary"):
                return Response(
                    content=res["content"],
                    media_type=res.get("content_type") or "application/octet-stream",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
# Lógica de decisão (if): Avalia 'if res.get("url"):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if res.get("url"):
                return RedirectResponse(
                    res["url"],
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
# Lógica de decisão (if): Avalia 'if res.get("data") and isinsta...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if res.get("data") and isinstance(res["data"], str):
                base64_str = res["data"]
                import base64
# Lógica de decisão (if): Avalia 'if "," in base64_str:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if "," in base64_str:
                    header, base64_str = base64_str.split(",", 1)
                    mime_type = header.split(";")[0].replace("data:", "") if "data:" in header else "application/octet-stream"
                else:
                    mime_type = res.get("mimeType") or res.get("mimetype") or "application/octet-stream"
                
                binary_data = base64.b64decode(base64_str)
                return Response(
                    content=binary_data,
                    media_type=mime_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
    except Exception as e:
        print(f"[CRM-MEDIA] Erro ao buscar mídia proxy para session={target_session}, msg={target_msg_id}: {e}", flush=True)

    raise HTTPException(status_code=404, detail="Mídia não encontrada ou indisponível.")




@router.get("/progressive/{contact_jid}")
async def get_progressive_assembled_profile(contact_jid: str, current_user: str = Depends(get_current_user)):
    """
    Retorna o perfil completo montado progressivamente no cache pelo contact_jid.
    """
    from app.services.n8n_service import ProgressiveContactCache
    profile = ProgressiveContactCache.get_assembled_payload(contact_jid)
# Lógica de decisão (if): Avalia 'if not profile:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
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
async def get_session_preference(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Retorna a sessão WhatsApp preferida do usuário para envio de mensagens."""
    user = db.query(User).filter(User.email == current_user).first()
# Lógica de decisão (if): Avalia 'if not user:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
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
# Lógica de decisão (if): Avalia 'if not user:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
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
# Lógica de decisão (if): Avalia 'if not user:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    session_id = payload.session_id or user.preferred_session_id
# Lógica de decisão (if): Avalia 'if not session_id:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma sessão WhatsApp selecionada. Escolha uma sessão em Conexões."
        )

    to_phone = getattr(payload, "contact_jid", None) or getattr(payload, "jid", None) or getattr(payload, "lead_id", None) or payload.phone
# Lógica de decisão (if): Avalia 'if not to_phone:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not to_phone:
        raise HTTPException(
            status_code=400,
            detail="Telefone/JID do destinatário é obrigatório."
        )

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
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
    user = db.query(User).filter(User.email == current_user).first()
# Lógica de decisão (if): Avalia 'if not user:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    active_session = payload.session_id or user.preferred_session_id
# Lógica de decisão (if): Avalia 'if not active_session:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not active_session:
        raise HTTPException(status_code=400, detail="Nenhuma sessão WhatsApp selecionada.")

    target_jid = payload.contact_jid
    media_text = payload.text or payload.caption or ""

    from app.services.whatsapp_service import get_tenant_id_for_user
    tenant_id = await get_tenant_id_for_user(user, db)
    from app.services.identity_service import get_m2m_jwt
    jwt_token = await get_m2m_jwt(tenant_id=tenant_id, scope="whatsapp:messages:send")

    from app.api.endpoints.whatsapp import make_whatsapp_api_request
    clean_path = f"/api/sessions/{active_session}/messages/send"

    wa_payload = {
        "jid": target_jid,
        "number": target_jid,
        "text": media_text,
        "media": {
            "kind": payload.media.kind,
            "mimeType": payload.media.mimeType or ("image/jpeg" if payload.media.kind == "image" else "audio/ogg; codecs=opus" if payload.media.kind == "audio" else "video/mp4" if payload.media.kind == "video" else "application/pdf"),
            "fileName": payload.media.fileName or f"file_{int(datetime.utcnow().timestamp())}",
            "data": payload.media.data
        }
    }

    headers = {
        "x-session-token": jwt_token,
        "x-tenant-id": tenant_id,
        "Authorization": f"Bearer {jwt_token}"
    }

    res = None
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        res = await make_whatsapp_api_request("POST", clean_path, headers=headers, json_data=wa_payload)
    except Exception as e:
        print(f"[SEND-MEDIA-BASE64] Transmissão para Whats API falhou: {e}", flush=True)

    from app.api.endpoints.webhooks import notify_lead_listeners, notify_crm_chat_listeners
    await notify_lead_listeners(target_jid, "reload")
    await notify_crm_chat_listeners(target_jid, is_from_me=True, sender="user")

    return {
        "status": "success",
        "session_id": active_session,
        "whatsapp_response": res
    }

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
# Lógica de repetição (for): Itera sobre elementos de 'for lead in leads:...' processando múltiplos dados em lote para as regras de domínio.
    for lead in leads:
        l_id = lead.get("id")
# Lógica de decisão (if): Avalia 'if lead.get("status") == "RESP...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if lead.get("status") == "RESPONDED":
            respostas_pendentes += 1
        elif l_id in MOCK_CONVERSATIONS and MOCK_CONVERSATIONS[l_id]:
# Lógica de decisão (if): Avalia 'if MOCK_CONVERSATIONS[l_id][-1...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
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
    """
    Classe ActivityCreatePayload.

    O que faz: Representa a estrutura de dados e operações para a entidade ActivityCreatePayload em o endpoint de API para crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ActivityCreatePayload, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
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
