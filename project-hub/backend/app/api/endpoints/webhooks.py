"""
Receptor Seguro de Webhooks Automáticos.
Processa chamadas recebidas via automações do N8N ou integradores de sistema. Exige assinaturas HMAC-SHA256 para comprovar a autenticidade e repassa a carga para processamento assíncrono das mensagens e leads.
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Header, Body, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import json
import asyncio
import secrets
import time
from cachetools import TTLCache

from app.core.database import get_db
from app.core.config import settings
from app.services.webhook_service import webhook_service
from app.core.auth import decode_access_token
from app.core.realtime_logger import log_realtime_event
from app.core.n8n_auth import authenticate_n8n_request

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
lead_listeners = {}     # {(tenant_id, lead_id): [(user_email, queue)]}
crm_chat_listeners: List[tuple] = [] # [(user_email, tenant_id, queue)]

async def notify_lead_listeners(lead_id: str, tenant_id: Optional[str] = None, event: str = "reload"):
    """
    Notifica listeners de eventos de lead em SSE, estritamente filtrado por tenant_id.
    """
    if not tenant_id:
        return
    key = (tenant_id, lead_id)
    if key in lead_listeners:
        for user_email, queue in list(lead_listeners[key]):
            await queue.put(event)

async def notify_crm_chat_listeners(
    lead_id: str,
    is_from_me: bool = False,
    sender: str = "lead",
    messages: Optional[List[Dict[str, Any]]] = None,
    tenant_id: Optional[str] = None
):
    """
    Função/Método notify_crm_chat_listeners.

    O que faz: Processa notify_crm_chat_listeners recebendo os parâmetros (lead_id, is_from_me, sender, messages, tenant_id) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação notify_crm_chat_listeners seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    import json
    all_jids = [lead_id] if lead_id and "{{" not in lead_id and "$" not in lead_id else []
    if messages:
        for msg in messages:
            if isinstance(msg, dict):
                if not tenant_id and msg.get("tenant_id"):
                    tenant_id = msg.get("tenant_id")
                for k in ["contact_jid", "chat_jid", "group_jid", "remoteJid", "lead_id"]:
                    val = msg.get(k)
                    if val and isinstance(val, str) and "{{" not in val and "$" not in val:
                        if val not in all_jids:
                            all_jids.append(val)

    if not tenant_id:
        log_realtime_event(
            "TENANT_RESOLUTION_FAILED",
            extra={
                "error": "Mensagem sem tenant_id identificado em notify_crm_chat_listeners",
                "lead_id": lead_id
            }
        )
        return

    primary_jid = all_jids[0] if all_jids else lead_id

    payload = json.dumps({
        "lead_id": primary_jid,
        "contact_jid": primary_jid,
        "all_jids": all_jids,
        "is_from_me": is_from_me,
        "sender": sender,
        "action": "new_message",
        "event": "new_message",
        "messages": messages or []
    })
    for user_email, listener_tenant_id, queue in list(crm_chat_listeners):
        if listener_tenant_id == tenant_id:
            await queue.put(payload)

@router.get("/events/leads/{lead_id}")
async def lead_events(
    lead_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Processa lead_events com autenticação via cabeçalho Authorization: Bearer e validação estrita de tenant.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticação obrigatório.")

    auth_token = auth_header[7:].strip()

    payload = decode_access_token(auth_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado")
    
    user_email = payload.get("sub", "unknown")
    user_tenant_id = payload.get("tenant_id")
    if not user_tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado: token sem tenant_id associado.")

    # Validar se o tenant_id do usuário coincide com o tenant do lead consultado no banco
    lead_tenant_id = None
    try:
        try:
            from app.models.lead import Lead
        except ImportError:
            from app.models import Lead
        db_lead = db.query(Lead).filter((Lead.id == lead_id) | (getattr(Lead, "remote_jid", Lead.id) == lead_id)).first()
        if db_lead:
            lead_tenant_id = getattr(db_lead, "tenant_id", None)
    except Exception:
        pass

    if not lead_tenant_id:
        try:
            from app.services.n8n_service import MOCK_LEADS
            for lead in MOCK_LEADS:
                if lead.get("id") == lead_id or lead.get("phone") == lead_id or lead.get("jid") == lead_id:
                    lead_tenant_id = lead.get("tenant_id")
                    break
        except Exception:
            pass

    if lead_tenant_id and lead_tenant_id != user_tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado: o tenant do lead não coincide com o do usuário")

    listener_key = (user_tenant_id, lead_id)
    queue = asyncio.Queue()
    if listener_key not in lead_listeners:
        lead_listeners[listener_key] = []
    lead_listeners[listener_key].append((user_email, queue))
    
    async def event_generator():
        """
        Gera eventos SSE de lead filtrados exclusivamente para o tenant do usuário.
        """
        try:
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
            if listener_key in lead_listeners:
                lead_listeners[listener_key] = [item for item in lead_listeners[listener_key] if item[1] != queue]
                if not lead_listeners[listener_key]:
                    del lead_listeners[listener_key]
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/events/crm-chats")
async def crm_chats_events(request: Request):
    """
    Processa crm_chats_events com autenticação JWT obrigatória via cabeçalho Authorization: Bearer e isolamento multi-tenant. Rejeita requisições anônimas.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticação obrigatório.")

    auth_token = auth_header[7:].strip()

    payload = decode_access_token(auth_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado.")

    user_email = payload.get("sub", "unknown")
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado: token sem tenant_id associado.")

    queue = asyncio.Queue()
    listener_entry = (user_email, tenant_id, queue)
    crm_chat_listeners.append(listener_entry)
    
    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        try:
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
            if listener_entry in crm_chat_listeners:
                crm_chat_listeners.remove(listener_entry)
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

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
    """
    body_bytes = await request.body()
    auth_info = authenticate_n8n_request(request, body_bytes)

    try:
        raw_body = json.loads(body_bytes) if body_bytes else await request.json()
        if isinstance(raw_body, dict):
            raw_body = [raw_body]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    if not isinstance(raw_body, list) or len(raw_body) == 0:
        raise HTTPException(status_code=400, detail="Payload must be a non-empty JSON array of message objects.")

    batch_tenant = None
    for item in raw_body:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each item in the payload array must be a JSON object.")
        if "is_from_me" not in item:
            item["is_from_me"] = item.get("fromMe", item.get("from_me", False))
        if "message_id" not in item and "id" in item:
            item["message_id"] = item["id"]
        if "contact_jid" not in item and "contact_id" in item:
            item["contact_jid"] = item["contact_id"]
        if "session_id" not in item and "session" in item:
            item["session_id"] = item["session"]
        if "tenant_id" not in item and "tenant" in item:
            item["tenant_id"] = item["tenant"]
        if "message_id" not in item:
            raise HTTPException(status_code=400, detail="Campo obrigatório ausente: message_id")
        if "contact_jid" not in item:
            raise HTTPException(status_code=400, detail="Campo obrigatório ausente: contact_jid")
        if "session_id" not in item:
            raise HTTPException(status_code=400, detail="Campo obrigatório ausente: session_id")
        if "tenant_id" not in item:
            raise HTTPException(status_code=400, detail="Campo obrigatório ausente: tenant_id")

        if batch_tenant is None:
            batch_tenant = item["tenant_id"]
        elif item["tenant_id"] != batch_tenant:
            raise HTTPException(status_code=400, detail="Inconsistência de tenant: todas as mensagens do lote devem pertencer ao mesmo tenant.")

        if tenant_id and item["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Cross-tenant event injection rejected.")

    messages_list = raw_body
    
    resolved_contact_id = messages_list[0].get("contact_jid") if messages_list else contact_id
    resolved_tenant_id = messages_list[0].get("tenant_id") if messages_list else tenant_id
    resolved_session_id = messages_list[0].get("session_id") if messages_list else session_id
    if not resolved_contact_id:
        raise HTTPException(status_code=400, detail="Missing contact_id or contact_jid parameter")

    explicit_from_me = messages_list[0].get("is_from_me", False) if messages_list else (is_from_me or False)
    explicit_sender = messages_list[0].get("participant_pushname", "lead") if messages_list else (sender or "lead")

    from app.services.n8n_service import n8n_service
    n8n_service.invalidate_leads_cache(tenant_id=resolved_tenant_id)

    final_is_from_me = explicit_from_me if explicit_from_me is not None else False
    final_sender = explicit_sender or ("user" if final_is_from_me else "lead")

    await notify_lead_listeners(resolved_contact_id, tenant_id=resolved_tenant_id, event="reload")
    await notify_crm_chat_listeners(resolved_contact_id, is_from_me=final_is_from_me, sender=final_sender, messages=messages_list, tenant_id=resolved_tenant_id)

    tenant_chat_listeners = [l for l in crm_chat_listeners if l[1] == resolved_tenant_id]
    notified_count = len(lead_listeners.get((resolved_tenant_id, resolved_contact_id), [])) + len(tenant_chat_listeners)
    return {
        "status": "success",
        "contact_id": resolved_contact_id,
        "lead_id": resolved_contact_id,
        "tenant_id": resolved_tenant_id,
        "session_id": resolved_session_id,
        "is_from_me": final_is_from_me,
        "sender": final_sender,
        "messages_received": len(messages_list),
        "notified_sessions": notified_count,
        "active_clients_connected": len(tenant_chat_listeners)
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
    Impacto na regra de negócio: Trata webhooks enviando formulários (application/x-www-form-urlencoded) com JSON serializado ou payloads nativos em JSON.
    """
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload_str = form_data.get("payload")
        if not payload_str:
            return dict(form_data)
        try:
            return json.loads(payload_str)
        except Exception:
            return dict(form_data)
    else:
        try:
            body = await request.json()
            if isinstance(body, str):
                try:
                    return json.loads(body)
                except Exception:
                    pass
            return body if isinstance(body, dict) else {}
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

@router.post("/inbound/whatsapp")
async def whatsapp_inbound_webhook(request: Request):
    """
    Inbound webhook for WhatsApp messages via n8n.
    Exige autenticação HMAC canônica n8n (timestamp.event_id.body).
    """
    body_bytes = await request.body()
    auth_info = authenticate_n8n_request(request, body_bytes)

    try:
        payload = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")

    lead_id = payload.get("lead_id")
    message_text = payload.get("message")
    sender = payload.get("sender", "lead")
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id é obrigatório.")
    if not lead_id or not message_text:
        raise HTTPException(status_code=400, detail="lead_id e message são obrigatórios.")

    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS, n8n_service
    n8n_service.invalidate_leads_cache(tenant_id=tenant_id)

    new_msg = {
        "id": f"msg_in_{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}",
        "sender": sender,
        "message": message_text,
        "channel": "whatsapp",
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    }
    if lead_id not in MOCK_CONVERSATIONS:
        MOCK_CONVERSATIONS[lead_id] = []
    MOCK_CONVERSATIONS[lead_id].append(new_msg)

    # Update last interaction timestamp on lead
    for lead in MOCK_LEADS:
        if lead["id"] == lead_id:
            lead["last_interaction"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
            if sender == "lead":
                lead["status"] = "RESPONDED"
            break

    # Notify listeners in real time
    await notify_lead_listeners(lead_id, tenant_id=tenant_id, event="reload")
    await notify_crm_chat_listeners(lead_id, tenant_id=tenant_id)

    return {"status": "success", "message": new_msg}


@router.post("/inbound/instagram")
async def instagram_inbound_webhook(request: Request):
    """
    Inbound webhook for Instagram messages via n8n.
    Exige autenticação HMAC canônica n8n (timestamp.event_id.body).
    """
    body_bytes = await request.body()
    auth_info = authenticate_n8n_request(request, body_bytes)

    try:
        payload = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")

    lead_id = payload.get("lead_id")
    message_text = payload.get("message")
    sender = payload.get("sender", "lead")
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id é obrigatório.")
    if not lead_id or not message_text:
        raise HTTPException(status_code=400, detail="lead_id e message são obrigatórios.")

    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS, n8n_service
    n8n_service.invalidate_leads_cache(tenant_id=tenant_id)

    new_msg = {
        "id": f"msg_in_{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}",
        "sender": sender,
        "message": message_text,
        "channel": "instagram",
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    }
    if lead_id not in MOCK_CONVERSATIONS:
        MOCK_CONVERSATIONS[lead_id] = []
    MOCK_CONVERSATIONS[lead_id].append(new_msg)

    # Update last interaction timestamp on lead
    for lead in MOCK_LEADS:
        if lead["id"] == lead_id:
            lead["last_interaction"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
            if sender == "lead":
                lead["status"] = "RESPONDED"
            break

    # Notify listeners in real time
    await notify_lead_listeners(lead_id, tenant_id=tenant_id, event="reload")
    await notify_crm_chat_listeners(lead_id, tenant_id=tenant_id)

    return {"status": "success", "message": new_msg}


@router.post("/waha/session-status")
async def waha_session_status_webhook(request: Request):
    """
    Endpoint to receive session status updates via n8n.
    Exige autenticação HMAC canônica n8n (timestamp.event_id.body).
    """
    body_bytes = await request.body()
    auth_info = authenticate_n8n_request(request, body_bytes)

    try:
        payload = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")

    session_id = payload.get("session")
    event_type = payload.get("event")

    inner_payload = payload.get("payload", {})
    status = inner_payload.get("status", "").upper() if isinstance(inner_payload, dict) else ""
    event_tenant_id = (inner_payload.get("tenant_id") if isinstance(inner_payload, dict) else None) or payload.get("tenant_id")
    if not event_tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id é obrigatório.")

    if event_type == "session.status" and status in ["STOPPED", "FAILED", "DISCONNECTED", "UNPAIRED", "TIMEOUT"]:
        # Broadcast to all CRM chat listeners of matching tenant that a session has disconnected
        msg = json.dumps({
            "action": "session_disconnected",
            "session_id": session_id,
            "status": status,
            "message": f"A sessão '{session_id}' foi desconectada."
        })
        for user_email, listener_tenant_id, queue in list(crm_chat_listeners):
            if listener_tenant_id == event_tenant_id:
                await queue.put(msg)

    return {"status": "success"}


@router.post("/outbound/whatsapp/send")
async def n8n_outbound_whatsapp_send(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Envio outbound acionado pelo n8n via WhatsAppClient.
    Exige autenticação HMAC canônica do n8n e resolução estrita de ownership de sessão no banco de dados.
    Rejeita incondicionalmente X-Master-API-Key e fallbacks para admin/default.
    """
    # 1. Rejeição explícita de X-Master-API-Key
    if request.headers.get("X-Master-API-Key") or request.headers.get("X-API-Key"):
        raise HTTPException(status_code=401, detail="X-Master-API-Key não é permitida.")

    # 2. Autenticação obrigatória n8n via HMAC canônica (timestamp.event_id.body)
    body_bytes = await request.body()
    auth_info = authenticate_n8n_request(request, body_bytes)

    try:
        payload = json.loads(body_bytes) if body_bytes else {}
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload deve ser um objeto JSON.")
    except Exception:
        raise HTTPException(status_code=400, detail="JSON payload inválido.")

    # 3. Exigência estrita de tenant_id e session_id (sem fallbacks para admin ou default)
    tenant_id = payload.get("tenant_id")
    session_id = payload.get("session_id")
    if not tenant_id or str(tenant_id).strip() == "" or str(tenant_id).lower() == "default":
        raise HTTPException(status_code=400, detail="tenant_id é obrigatório e não pode ser default.")
    if not session_id or str(session_id).strip() == "" or str(session_id).lower() == "default":
        raise HTTPException(status_code=400, detail="session_id é obrigatório e não pode ser default.")

    # 4. Prova positiva de vínculo da sessão no banco de dados para o tenant
    from app.models.whatsapp_account import WhatsappAccount
    account = db.query(WhatsappAccount).filter(
        WhatsappAccount.tenant_id == tenant_id,
        WhatsappAccount.session_id == session_id
    ).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail=f"Sessão '{session_id}' não encontrada ou não vinculada ao tenant '{tenant_id}'."
        )

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

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    final_jid = phone if "@" in str(phone) else f"{cleaned_phone}@s.whatsapp.net"

    from app.services.whatsapp_client import whatsapp_client

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

    res = await whatsapp_client.send_message(
        tenant_id=tenant_id,
        session_id=account.session_id,
        message_data=json_data
    )

    return JSONResponse(status_code=200, content=res)

