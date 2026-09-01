"""
Receptor Seguro de Webhooks Automáticos.
Processa chamadas recebidas via automações do N8N ou integradores de sistema. Exige assinaturas HMAC-SHA256 para comprovar a autenticidade e repassa a carga para processamento assíncrono das mensagens e leads.
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Header, Body, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import json
import asyncio
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.services.webhook_service import webhook_service
from app.models.user import User
from app.services.whatsapp_service import get_tenant_id_for_user

router = APIRouter()

from pydantic import BaseModel

class LeadChatUpdateRequest(BaseModel):
    """
    Classe LeadChatUpdateRequest.

    O que faz: Representa a estrutura de dados e operações para a entidade LeadChatUpdateRequest em o endpoint de API para webhooks.
    Impacto na regra de negócio: Centraliza o comportamento da entidade LeadChatUpdateRequest, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    lead_id: str

# In-memory queues for Server-Sent Events (SSE)
project_listeners = {}  # {public_token: [asyncio.Queue]}
global_listeners = []   # [asyncio.Queue]
lead_listeners: Dict[tuple[str, str, str], List[tuple[str, asyncio.Queue]]] = {}
# {(tenant_id, session_id, contact_jid): [(user_email, queue)]}
crm_chat_listeners: Dict[str, List[tuple[str, asyncio.Queue, str]]] = {}  # {tenant_id: [(user_email, queue, session_id)]}


def _lead_listener_key(
    lead_id: Optional[str],
    session_id: Optional[str],
    tenant_id: Optional[str],
) -> Optional[tuple[str, str, str]]:
    """The legacy lead stream must never fall back to a shared contact key."""
    contact_jid = str(lead_id or "").split("___", 1)[0].strip()
    resolved_session = str(session_id or "").strip()
    resolved_tenant = str(tenant_id or "").strip()
    if not contact_jid or not resolved_session or not resolved_tenant:
        return None
    return resolved_tenant, resolved_session, contact_jid


async def _tenant_for_sse_subscriber(payload: Dict[str, Any], db: Session) -> tuple[str, str]:
    """Uses the current database assignment instead of a possibly stale JWT claim."""
    user_email = str(payload.get("sub") or "").strip()
    if not user_email:
        raise HTTPException(status_code=401, detail="Authentication with a user is required")
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user was not found")
    return user_email, await get_tenant_id_for_user(user, db)


async def notify_lead_listeners(
    lead_id: str,
    event: str = "reload",
    *,
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """
    Função/Método notify_lead_listeners.

    O que faz: Processa notify_lead_listeners recebendo os parâmetros (lead_id, event) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação notify_lead_listeners seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    listener_key = _lead_listener_key(lead_id, session_id, tenant_id)
    if listener_key is None:
        return
    if listener_key in lead_listeners:
        for user_email, queue in list(lead_listeners[listener_key]):
            await queue.put(event)

async def notify_crm_chat_listeners(
    lead_id: str,
    is_from_me: bool = False,
    sender: str = "lead",
    messages: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """
    Função/Método notify_crm_chat_listeners.

    O que faz: Processa notify_crm_chat_listeners recebendo os parâmetros (lead_id, is_from_me, sender, messages) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação notify_crm_chat_listeners seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # A CRM event without a tenant cannot be safely delivered to a connected
    # operator. Dropping it is safer than recreating the legacy shared inbox.
    if not tenant_id:
        return

    import json
    all_jids = [lead_id] if lead_id and "{{" not in lead_id and "$" not in lead_id else []
    if messages:
        for msg in messages:
            if isinstance(msg, dict):
                for k in ["contact_jid", "chat_jid", "group_jid", "remoteJid", "lead_id"]:
                    val = msg.get(k)
                    if val and isinstance(val, str) and "{{" not in val and "$" not in val:
                        if val not in all_jids:
                            all_jids.append(val)

    primary_jid = all_jids[0] if all_jids else lead_id
    resolved_session_id = session_id
    if not resolved_session_id and messages:
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            resolved_session_id = msg.get("session_id") or msg.get("session") or msg.get("whatsapp_instance")
            if resolved_session_id:
                break
    if not resolved_session_id:
        return

    payload = json.dumps({
        "lead_id": primary_jid,
        "contact_jid": primary_jid,
        "all_jids": all_jids,
        "is_from_me": is_from_me,
        "sender": sender,
        "tenant_id": tenant_id,
        "session_id": resolved_session_id,
        "action": "new_message",
        "event": "new_message",
        "messages": messages or []
    })
    for user_email, queue, listener_session_id in list(crm_chat_listeners.get(tenant_id, [])):
        if listener_session_id and listener_session_id != resolved_session_id:
            continue
        await queue.put(payload)

@router.get("/events/leads/{lead_id}")
async def lead_events(
    lead_id: str,
    token: str,
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Função/Método lead_events.

    O que faz: Processa lead_events recebendo os parâmetros (lead_id, token, request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação lead_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    from app.core.auth import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado")
    
    user_email, tenant_id = await _tenant_for_sse_subscriber(payload, db)
    listener_key = _lead_listener_key(lead_id, session_id, tenant_id)
    if listener_key is None:
        raise HTTPException(status_code=400, detail="session_id is required")
    queue = asyncio.Queue()
    lead_listeners.setdefault(listener_key, []).append((user_email, queue))
    
    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            listeners = lead_listeners.get(listener_key, [])
            if listener in listeners:
                listeners.remove(listener)
            if not listeners:
                lead_listeners.pop(listener_key, None)
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/events/crm-chats")
async def crm_chats_events(
    request: Request,
    session_id: Optional[str] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Função/Método crm_chats_events.

    O que faz: Processa crm_chats_events recebendo os parâmetros (request, token) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação crm_chats_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    from app.core.auth import decode_access_token
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="Authentication with a tenant is required")
    user_email, tenant_id = await _tenant_for_sse_subscriber(payload, db)

    queue = asyncio.Queue()
    listener = (user_email, queue, session_id or "")
    crm_chat_listeners.setdefault(tenant_id, []).append(listener)
    
    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            tenant_listeners = crm_chat_listeners.get(tenant_id, [])
            if listener in tenant_listeners:
                tenant_listeners.remove(listener)
            if not tenant_listeners:
                crm_chat_listeners.pop(tenant_id, None)
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

def _event_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _event_session_id(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("id") or value.get("session_id")
    return _event_text(value)


def _event_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "sim"}
    return bool(value)


def _normalize_chat_event_message(
    raw_message: Dict[str, Any],
    *,
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    message_id: Optional[str] = None,
    jid: Optional[str] = None,
    phone: Optional[str] = None,
    is_from_me: Optional[bool] = None,
    sender: Optional[str] = None,
) -> Dict[str, Any]:
    """Validates the n8n event scope before it is delivered to an operator."""
    message = dict(raw_message)
    key = message.get("key") if isinstance(message.get("key"), dict) else {}
    resolved_message_id = _event_text(
        message.get("message_id") or message.get("id") or key.get("id") or message_id
    )
    resolved_contact_id = _event_text(
        message.get("contact_jid")
        or message.get("contact_id")
        or message.get("chat_jid")
        or message.get("jid")
        or message.get("remoteJid")
        or key.get("remoteJid")
        or contact_id
        or lead_id
        or jid
        or phone
    )
    resolved_session_id = _event_session_id(
        message.get("session_id") or message.get("session") or message.get("whatsapp_instance") or session_id
    )
    resolved_tenant_id = _event_text(message.get("tenant_id") or message.get("tenant") or tenant_id)
    if not resolved_message_id:
        raise ValueError("message_id is required")
    if not resolved_contact_id:
        raise ValueError("contact_jid is required")
    if not resolved_session_id:
        raise ValueError("session_id is required")
    if not resolved_tenant_id:
        raise ValueError("tenant_id is required")

    from_me = _event_bool(
        message.get("is_from_me", message.get("from_me", message.get("fromMe", is_from_me or False)))
    )
    raw_sender = _event_text(message.get("sender") or sender).lower()
    normalized_sender = "user" if from_me or raw_sender in {"user", "me", "operator"} else "lead"
    message.update({
        "id": message.get("id") or resolved_message_id,
        "message_id": resolved_message_id,
        "contact_jid": resolved_contact_id,
        "session_id": resolved_session_id,
        "tenant_id": resolved_tenant_id,
        "is_from_me": normalized_sender == "user",
        "sender": normalized_sender,
    })
    return message


async def _process_update_chat(
    request: Request,
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    id: Optional[str] = None,
    jid: Optional[str] = None,
    phone: Optional[str] = None,
    is_from_me: Optional[bool] = None,
    sender: Optional[str] = None
):
    """
    Função/Método _process_update_chat.

    O que faz: Processa _process_update_chat recebendo os parâmetros (request, contact_id, lead_id, tenant_id, session_id, id, jid, phone, is_from_me, sender) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação _process_update_chat seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    try:
        raw_body = await request.json()
        if isinstance(raw_body, dict):
            raw_body = [raw_body]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    if not isinstance(raw_body, list):
        raise HTTPException(status_code=400, detail="Payload must be a JSON array of message objects.")
    messages_list: List[Dict[str, Any]] = []
    for item in raw_body:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each item in the payload array must be a JSON object.")
        try:
            messages_list.append(_normalize_chat_event_message(
                item,
                contact_id=contact_id,
                lead_id=lead_id,
                tenant_id=tenant_id,
                session_id=session_id,
                message_id=id,
                jid=jid,
                phone=phone,
                is_from_me=is_from_me,
                sender=sender,
            ))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=f"Invalid CRM message payload: {error}") from error

    if not messages_list:
        raise HTTPException(status_code=400, detail="At least one CRM message is required.")

    from app.services.n8n_service import n8n_service
    n8n_service.invalidate_leads_cache()

    message_groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for message in messages_list:
        group_key = (
            message["tenant_id"],
            message["session_id"],
            message["contact_jid"],
            message["is_from_me"],
            message["sender"],
        )
        message_groups.setdefault(group_key, []).append(message)

    notified_lead_scopes = set()
    notified_tenants = set()
    tenant_listener_count = 0
    for (message_tenant, message_session, message_contact, message_is_from_me, message_sender), grouped_messages in message_groups.items():
        lead_scope = _lead_listener_key(message_contact, message_session, message_tenant)
        if lead_scope and lead_scope not in notified_lead_scopes:
            await notify_lead_listeners(
                message_contact,
                "reload",
                session_id=message_session,
                tenant_id=message_tenant,
            )
            notified_lead_scopes.add(lead_scope)
        await notify_crm_chat_listeners(
            message_contact,
            is_from_me=message_is_from_me,
            sender=message_sender,
            messages=grouped_messages,
            session_id=message_session,
            tenant_id=message_tenant,
        )
        if message_tenant not in notified_tenants:
            notified_tenants.add(message_tenant)
            tenant_listener_count += len(crm_chat_listeners.get(message_tenant, []))

    first_message = messages_list[0]
    notified_count = sum(len(lead_listeners.get(scope, [])) for scope in notified_lead_scopes) + tenant_listener_count
    return {
        "status": "success",
        "contact_id": first_message["contact_jid"],
        "lead_id": first_message["contact_jid"],
        "tenant_id": first_message["tenant_id"],
        "session_id": first_message["session_id"],
        "is_from_me": first_message["is_from_me"],
        "sender": first_message["sender"],
        "messages_received": len(messages_list),
        "notified_sessions": notified_count,
        "active_clients_connected": tenant_listener_count,
        "notified_tenants": sorted(notified_tenants),
    }

@router.post("/crm/update-chat")
async def update_chat_webhook_post(
    request: Request,
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    id: Optional[str] = None,
    jid: Optional[str] = None,
    phone: Optional[str] = None,
    is_from_me: Optional[bool] = None,
    sender: Optional[str] = None
):
    """
    Função/Método update_chat_webhook_post.

    O que faz: Atualização e modificação de informações para update_chat_webhook_post recebendo os parâmetros (request, contact_id, lead_id, tenant_id, session_id, id, jid, phone, is_from_me, sender) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação update_chat_webhook_post seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return await _process_update_chat(
        request=request,
        contact_id=contact_id,
        lead_id=lead_id,
        tenant_id=tenant_id,
        session_id=session_id,
        id=id,
        jid=jid,
        phone=phone,
        is_from_me=is_from_me,
        sender=sender
    )

@router.get("/crm/update-chat")
async def update_chat_webhook_get(
    request: Request,
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    id: Optional[str] = None,
    jid: Optional[str] = None,
    phone: Optional[str] = None,
    is_from_me: Optional[bool] = None,
    sender: Optional[str] = None
):
    """
    Função/Método update_chat_webhook_get.

    O que faz: Atualização e modificação de informações para update_chat_webhook_get recebendo os parâmetros (request, contact_id, lead_id, tenant_id, session_id, id, jid, phone, is_from_me, sender) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação update_chat_webhook_get seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return await _process_update_chat(
        request=request,
        contact_id=contact_id,
        lead_id=lead_id,
        tenant_id=tenant_id,
        session_id=session_id,
        id=id,
        jid=jid,
        phone=phone,
        is_from_me=is_from_me,
        sender=sender
    )

async def notify_listeners(public_token: str):
    """
    Função/Método notify_listeners.

    O que faz: Processa notify_listeners recebendo os parâmetros (public_token) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação notify_listeners seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # Notify specific project listeners
    if public_token in project_listeners:
        for queue in list(project_listeners[public_token]):
            await queue.put("reload")
    # Notify global dashboard listeners
    for queue in list(global_listeners):
        await queue.put("reload")

@router.get("/events/{public_token}")
async def project_events(public_token: str, request: Request):
    """
    Função/Método project_events.

    O que faz: Processa project_events recebendo os parâmetros (public_token, request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação project_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    queue = asyncio.Queue()
    if public_token not in project_listeners:
        project_listeners[public_token] = []
    project_listeners[public_token].append(queue)
    
    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if public_token in project_listeners:
                if queue in project_listeners[public_token]:
                    project_listeners[public_token].remove(queue)
                if not project_listeners[public_token]:
                    del project_listeners[public_token]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/events")
async def all_projects_events(request: Request):
    """
    Função/Método all_projects_events.

    O que faz: Processa all_projects_events recebendo os parâmetros (request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação all_projects_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    queue = asyncio.Queue()
    global_listeners.append(queue)

    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in global_listeners:
                global_listeners.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def get_payload(request: Request) -> dict:
    """
    Função/Método get_payload.

    O que faz: Recuperação de dados cadastrados para get_payload recebendo os parâmetros (request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_payload seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload_str = form_data.get("payload")
        if not payload_str:
            return {}
        try:
            return json.loads(payload_str)
        except Exception:
            return {}
    else:
        try:
            return await request.json()
        except Exception:
            return {}

@router.post("/github/{public_token}")
async def github_webhook_by_token(public_token: str, request: Request, db: Session = Depends(get_db)):
    """
    Função/Método github_webhook_by_token.

    O que faz: Processa github_webhook_by_token recebendo os parâmetros (public_token, request, db) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação github_webhook_by_token seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # 1. Look up the project securely using the unique public_token
    from app.models.project import Project
    project = db.query(Project).filter(Project.public_token == public_token).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    payload = await get_payload(request)

    # 1.5 Detect Netlify Deploy webhook
    if "site_id" in payload or "deploy_url" in payload:
        netlify_event = request.headers.get("x-netlify-event", "deploy-succeeded")
        status = "SUCCESS"
        if "succeeded" in netlify_event.lower() or netlify_event in ("deploy_created", "deploy-succeeded"):
            status = "SUCCESS"
        elif "failed" in netlify_event.lower():
            status = "FAILED"
            
        deploy_url = payload.get("deploy_url") or payload.get("ssl_url") or payload.get("url")
        created_at_str = payload.get("created_at")
        try:
            if created_at_str:
                if created_at_str.endswith("Z"):
                    created_at_str = created_at_str.replace("Z", "+00:00")
                deploy_date = datetime.fromisoformat(created_at_str)
            else:
                deploy_date = datetime.now(timezone.utc).replace(tzinfo=None)
        except Exception:
            deploy_date = datetime.now(timezone.utc).replace(tzinfo=None)

        webhook_service.process_deploy_webhook(
            db=db,
            project_id=project.id,
            provider="netlify",
            status=status,
            deploy_url=deploy_url,
            deploy_date=deploy_date
        )
        await notify_listeners(public_token)
        return {"status": "success", "type": "netlify_deploy"}

    # 2. Native GitHub push payload format
    if "commits" in payload:
        commits = payload.get("commits", [])
        processed_count = 0
        for c in commits:
            commit_hash = c.get("id")
            message = c.get("message")
            author = c.get("author", {}).get("name", "Unknown")
            date_str = c.get("timestamp")
            if not (commit_hash and message):
                continue
            try:
                if date_str and date_str.endswith("Z"):
                    date_str = date_str.replace("Z", "+00:00")
                commit_date = datetime.fromisoformat(date_str) if date_str else datetime.now(timezone.utc).replace(tzinfo=None)
            except Exception:
                commit_date = datetime.now(timezone.utc).replace(tzinfo=None)

            webhook_service.process_github_webhook(
                db=db,
                project_id=project.id,
                commit_hash=commit_hash,
                message=message,
                author=author,
                commit_date=commit_date
            )
            processed_count += 1
            
        await notify_listeners(public_token)
        return {"status": "success", "processed_commits": processed_count}

    # 3. Custom mock payload format fallback
    commit_hash = payload.get("commit_hash")
    message = payload.get("commit_message")
    author = payload.get("author")
    date_str = payload.get("date")
    if not all([commit_hash, message, author, date_str]):
        return {"status": "ignored", "reason": "missing fields"}
    try:
        commit_date = datetime.fromisoformat(date_str)
    except ValueError:
        commit_date = datetime.now(timezone.utc).replace(tzinfo=None)

    webhook_service.process_github_webhook(
        db=db,
        project_id=project.id,
        commit_hash=commit_hash,
        message=message,
        author=author,
        commit_date=commit_date
    )

    await notify_listeners(public_token)
    return {"status": "success"}

@router.post("/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Função/Método github_webhook.

    O que faz: Processa github_webhook recebendo os parâmetros (request, db) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação github_webhook seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # Supports both standard GitHub push webhook payloads and the custom mock payload
    payload = await get_payload(request)

    # 1. Native GitHub push payload format
    if "repository" in payload and "commits" in payload:
        repo_url = payload.get("repository", {}).get("html_url")
        if not repo_url:
            return {"status": "ignored", "reason": "repository html_url missing"}

        # Look up project by matching github_url
        from app.models.project import Project
        search_url = repo_url.rstrip("/")
        project = db.query(Project).filter(
            (Project.github_url.like(f"%{search_url}%")) | 
            (Project.github_url.like(f"%{search_url}.git%"))
        ).first()
        if not project:
            return {"status": "ignored", "reason": f"no project found matching github_url: {repo_url}"}

        commits = payload.get("commits", [])
        processed_count = 0
        for c in commits:
            commit_hash = c.get("id")
            message = c.get("message")
            author = c.get("author", {}).get("name", "Unknown")
            date_str = c.get("timestamp")
            if not (commit_hash and message):
                continue
            try:
                if date_str and date_str.endswith("Z"):
                    date_str = date_str.replace("Z", "+00:00")
                commit_date = datetime.fromisoformat(date_str) if date_str else datetime.now(timezone.utc).replace(tzinfo=None)
            except Exception:
                commit_date = datetime.now(timezone.utc).replace(tzinfo=None)

            webhook_service.process_github_webhook(
                db=db,
                project_id=project.id,
                commit_hash=commit_hash,
                message=message,
                author=author,
                commit_date=commit_date
            )
            processed_count += 1
            
        await notify_listeners(project.public_token)
        return {"status": "success", "processed_commits": processed_count}

    # 2. Custom mock payload format fallback
    project_id = payload.get("project_id")
    commit_hash = payload.get("commit_hash")
    message = payload.get("commit_message")
    author = payload.get("author")
    date_str = payload.get("date")
    if not all([project_id, commit_hash, message, author, date_str]):
        return {"status": "ignored", "reason": "missing fields"}
    try:
        commit_date = datetime.fromisoformat(date_str)
    except ValueError:
        commit_date = datetime.now(timezone.utc).replace(tzinfo=None)

    webhook_service.process_github_webhook(
        db=db,
        project_id=project_id,
        commit_hash=commit_hash,
        message=message,
        author=author,
        commit_date=commit_date
    )

    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        await notify_listeners(project.public_token)

    return {"status": "success"}

@router.post("/deploy")
async def deploy_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Função/Método deploy_webhook.

    O que faz: Processa deploy_webhook recebendo os parâmetros (request, db) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação deploy_webhook seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    payload = await request.json()

    project_id = payload.get("project_id")
    provider = payload.get("provider") # netlify, vercel
    status = payload.get("status")
    deploy_url = payload.get("deploy_url")
    date_str = payload.get("deploy_date")
    if not all([project_id, provider, status, date_str]):
        return {"status": "ignored", "reason": "missing fields"}
    try:
        deploy_date = datetime.fromisoformat(date_str)
    except ValueError:
        deploy_date = datetime.now(timezone.utc).replace(tzinfo=None)

    webhook_service.process_deploy_webhook(
        db=db,
        project_id=project_id,
        provider=provider,
        status=status,
        deploy_url=deploy_url,
        deploy_date=deploy_date
    )

    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        await notify_listeners(project.public_token)

    return {"status": "success"}

async def _process_legacy_inbound_message(request: Request, channel: str):
    """Publishes a scoped event after the n8n workflow persisted the message."""
    signature = request.headers.get("X-Signature")
    if hasattr(settings, "WEBHOOK_SECRET") and settings.WEBHOOK_SECRET:
        import hmac
        import hashlib
        body = await request.body()
        expected_signature = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected_signature):
            return {"status": "ignored", "reason": "invalid signature"}

    payload = await request.json()
    lead_id = payload.get("lead_id")
    message_text = payload.get("message")
    sender = payload.get("sender", "lead")
    tenant_id = payload.get("tenant_id") or payload.get("tenant")
    session_id = payload.get("session_id") or payload.get("session")
    if not lead_id or not message_text:
        return {"status": "ignored", "reason": "missing lead_id or message"}
    if not tenant_id or not session_id:
        return {"status": "ignored", "reason": "missing tenant_id or session_id"}

    message_id = (
        payload.get("message_id")
        or payload.get("id")
        or (payload.get("key") or {}).get("id")
        or f"inbound_{uuid.uuid4().hex}"
    )
    try:
        new_msg = _normalize_chat_event_message({
            "id": message_id,
            "message_id": message_id,
            "sender": sender,
            "is_from_me": payload.get("is_from_me", payload.get("from_me", payload.get("fromMe", False))),
            "message": message_text,
            "content": message_text,
            "channel": channel,
            "message_type": payload.get("message_type") or payload.get("type"),
            "status": payload.get("status"),
            "message_timestamp": payload.get("message_timestamp") or payload.get("timestamp") or datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "contact_jid": lead_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
        })
    except ValueError as error:
        raise HTTPException(status_code=400, detail=f"Invalid inbound message: {error}") from error

    from app.services.n8n_service import n8n_service
    n8n_service.invalidate_leads_cache()

    await notify_lead_listeners(
        new_msg["contact_jid"],
        "reload",
        session_id=new_msg["session_id"],
        tenant_id=new_msg["tenant_id"],
    )
    await notify_crm_chat_listeners(
        new_msg["contact_jid"],
        is_from_me=new_msg["is_from_me"],
        sender=new_msg["sender"],
        messages=[new_msg],
        session_id=new_msg["session_id"],
        tenant_id=new_msg["tenant_id"],
    )
    return {"status": "success", "message": new_msg}


@router.post("/inbound/whatsapp")
async def whatsapp_inbound_webhook(request: Request):
    """Inbound WhatsApp notification after persistence by n8n."""
    return await _process_legacy_inbound_message(request, channel="whatsapp")

@router.post("/inbound/instagram")
async def instagram_inbound_webhook(request: Request):
    """Inbound Instagram notification after persistence by n8n."""
    return await _process_legacy_inbound_message(request, channel="instagram")
@router.post("/waha/session-status")
async def waha_session_status_webhook(request: Request):
    """
    Endpoint to receive session status updates from WAHA.
    If a session drops or fails, we notify the frontend via SSE.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid json"}
        
    session_id = payload.get("session")
    event_type = payload.get("event")
    
    # WAHA usually sends event="session.status" and payload.status
    inner_payload = payload.get("payload", {})
    status = inner_payload.get("status", "").upper() if isinstance(inner_payload, dict) else ""
    tenant_id = payload.get("tenant_id") or (inner_payload.get("tenant_id") if isinstance(inner_payload, dict) else None)
    if event_type == "session.status" and status in ["STOPPED", "FAILED", "DISCONNECTED", "UNPAIRED", "TIMEOUT"]:
        # Broadcast only to the tenant that owns the disconnected session.
        msg = json.dumps({
            "action": "session_disconnected",
            "session_id": session_id,
            "status": status,
            "message": f"A sessão '{session_id}' foi desconectada."
        })
        if tenant_id:
            for user_email, queue in list(crm_chat_listeners.get(tenant_id, [])):
                await queue.put(msg)
            
    return {"status": "success"}

@router.post("/outbound/whatsapp/send")
async def n8n_outbound_whatsapp_send(
    payload: Dict[str, Any] = Body(...),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db)
):
    if not x_master_api_key or x_master_api_key != settings.WHATSAPP_MASTER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")

    session_id = payload.get("session_id")
    phone = payload.get("phone") or payload.get("number") or payload.get("jid") or payload.get("contact_jid")
    message = payload.get("message") or payload.get("text")
    media = payload.get("media")
    base64_content = payload.get("base64_content")
    
    if base64_content and not media:
        media = {
            "data": base64_content,
            "mimeType": payload.get("mimeType") or "application/pdf",
            "fileName": payload.get("fileName") or "documento.pdf",
            "kind": payload.get("kind") or "document"
        }

    if not phone:
        raise HTTPException(status_code=400, detail="Missing phone, number or jid")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    final_jid = phone if "@" in str(phone) else f"{cleaned_phone}@s.whatsapp.net"
    
    from app.api.endpoints.whatsapp import make_whatsapp_api_request
    from app.services.identity_service import get_m2m_jwt
    
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant_id")
    jwt_token = await get_m2m_jwt(tenant_id=tenant_id, scope="whatsapp:messages:send")
    
    headers = {
        "X-Master-API-Key": settings.WHATSAPP_MASTER_SECRET,
        "x-tenant-id": tenant_id,
        "x-session-token": jwt_token,
        "Authorization": f"Bearer {jwt_token}"
    }
    
    json_data = {
        "phone": cleaned_phone,
        "number": cleaned_phone,
        "jid": final_jid
    }
    if message:
        json_data["message"] = message
        json_data["text"] = message
    if media:
        json_data["media"] = media
        
    for k, v in payload.items():
        if k not in ["phone", "number", "message", "text", "session_id", "tenant_id", "jid", "contact_jid", "master_api_key", "x_master_api_key", "base64_content", "media", "mimeType", "fileName", "kind"]:
            json_data[k] = v

    res = await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers=headers,
        json_data=json_data,
        timeout=30.0
    )
    
    return JSONResponse(status_code=200, content=res)
