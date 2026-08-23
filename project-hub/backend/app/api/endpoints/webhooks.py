from fastapi import APIRouter, Depends, Request, HTTPException, Header, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import asyncio

from app.core.database import get_db
from app.core.config import settings
from app.services.webhook_service import webhook_service

router = APIRouter()

from pydantic import BaseModel

class LeadChatUpdateRequest(BaseModel):
    lead_id: str

# In-memory queues for Server-Sent Events (SSE)
project_listeners = {}  # {public_token: [asyncio.Queue]}
global_listeners = []   # [asyncio.Queue]
lead_listeners = {}     # {lead_id: [(user_email, queue)]}
crm_chat_listeners = [] # [(user_email, queue)]

async def notify_lead_listeners(lead_id: str, event: str = "reload"):
    if lead_id in lead_listeners:
        for user_email, queue in list(lead_listeners[lead_id]):
            await queue.put(event)

async def notify_crm_chat_listeners(lead_id: str, is_from_me: bool = False, sender: str = "lead", messages: Optional[List[Dict[str, Any]]] = None):
    import json
    all_jids = [lead_id] if lead_id and "{{" not in lead_id and "$" not in lead_id else []
    if messages:
        for msg in messages:
            if isinstance(msg, dict):
                for k in ["contact_jid", "chat_jid", "group_jid", "remoteJid", "lead_id", "jid", "phone", "participant"]:
                    val = msg.get(k)
                    if val and isinstance(val, str) and "{{" not in val and "$" not in val:
                        if val not in all_jids:
                            all_jids.append(val)

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
    for user_email, queue in list(crm_chat_listeners):
        await queue.put(payload)

@router.get("/events/leads/{lead_id}")
async def lead_events(lead_id: str, token: str, request: Request):
    from app.core.auth import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado")
    
    user_email = payload.get("sub", "unknown")
    queue = asyncio.Queue()
    
    if lead_id not in lead_listeners:
        lead_listeners[lead_id] = []
    lead_listeners[lead_id].append((user_email, queue))
    
    async def event_generator():
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
            if lead_id in lead_listeners:
                lead_listeners[lead_id] = [item for item in lead_listeners[lead_id] if item[1] != queue]
                if not lead_listeners[lead_id]:
                    del lead_listeners[lead_id]
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/events/crm-chats")
async def crm_chats_events(request: Request, token: Optional[str] = None):
    user_email = "anonymous"
    if token:
        try:
            from app.core.auth import decode_access_token
            payload = decode_access_token(token)
            if payload:
                user_email = payload.get("sub", "unknown")
        except Exception:
            pass

    queue = asyncio.Queue()
    crm_chat_listeners.append((user_email, queue))
    
    async def event_generator():
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
            if (user_email, queue) in crm_chat_listeners:
                crm_chat_listeners.remove((user_email, queue))
                    
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
    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(raw_body, list):
        raise HTTPException(status_code=400, detail="Payload must be a JSON array of message objects.")

    for item in raw_body:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each item in the payload array must be a JSON object.")
        if "message_id" not in item:
            raise HTTPException(status_code=400, detail="Missing required field: message_id")
        if "contact_jid" not in item:
            raise HTTPException(status_code=400, detail="Missing required field: contact_jid")
        if "session_id" not in item:
            raise HTTPException(status_code=400, detail="Missing required field: session_id")
        if "tenant_id" not in item:
            raise HTTPException(status_code=400, detail="Missing required field: tenant_id")

    messages_list = raw_body
    
    resolved_contact_id = messages_list[0].get("contact_jid") if messages_list else contact_id
    resolved_tenant_id = messages_list[0].get("tenant_id") if messages_list else tenant_id
    resolved_session_id = messages_list[0].get("session_id") if messages_list else session_id

    if not resolved_contact_id:
        raise HTTPException(status_code=400, detail="Missing contact_id or contact_jid parameter")

    explicit_from_me = messages_list[0].get("is_from_me", False) if messages_list else (is_from_me or False)
    explicit_sender = messages_list[0].get("participant_pushname", "lead") if messages_list else (sender or "lead")

    from app.services.n8n_service import n8n_service
    n8n_service.invalidate_leads_cache()

    final_is_from_me = explicit_from_me if explicit_from_me is not None else False
    final_sender = explicit_sender or ("user" if final_is_from_me else "lead")

    await notify_lead_listeners(resolved_contact_id, "reload")
    await notify_crm_chat_listeners(resolved_contact_id, is_from_me=final_is_from_me, sender=final_sender, messages=messages_list)

    notified_count = len(lead_listeners.get(resolved_contact_id, [])) + len(crm_chat_listeners)
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
        "active_clients_connected": len(crm_chat_listeners)
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
    # Notify specific project listeners
    if public_token in project_listeners:
        for queue in list(project_listeners[public_token]):
            await queue.put("reload")
    # Notify global dashboard listeners
    for queue in list(global_listeners):
        await queue.put("reload")

@router.get("/events/{public_token}")
async def project_events(public_token: str, request: Request):
    queue = asyncio.Queue()
    if public_token not in project_listeners:
        project_listeners[public_token] = []
    project_listeners[public_token].append(queue)
    
    async def event_generator():
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
    queue = asyncio.Queue()
    global_listeners.append(queue)

    async def event_generator():
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
                deploy_date = datetime.utcnow()
        except Exception:
            deploy_date = datetime.utcnow()

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
                commit_date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()
            except Exception:
                commit_date = datetime.utcnow()

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
        commit_date = datetime.utcnow()

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
                commit_date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()
            except Exception:
                commit_date = datetime.utcnow()

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
        commit_date = datetime.utcnow()

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
        deploy_date = datetime.utcnow()

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
    Inbound webhook for WhatsApp messages.
    Receives message payload and appends to in-memory conversation list.
    """
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
    
    if not lead_id or not message_text:
        return {"status": "ignored", "reason": "missing lead_id or message"}
        
    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS, n8n_service
    n8n_service.invalidate_leads_cache()
    
    new_msg = {
        "id": f"msg_in_{int(datetime.utcnow().timestamp())}",
        "sender": sender,
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
            if sender == "lead":
                lead["status"] = "RESPONDED" # Toggle status to responded
            break
            
    # Notify listeners in real time
    await notify_lead_listeners(lead_id, "reload")
    await notify_crm_chat_listeners(lead_id)
            
    return {"status": "success", "message": new_msg}

@router.post("/inbound/instagram")
async def instagram_inbound_webhook(request: Request):
    """
    Inbound webhook for Instagram messages.
    Receives message payload and appends to in-memory conversation list.
    """
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
    
    if not lead_id or not message_text:
        return {"status": "ignored", "reason": "missing lead_id or message"}
        
    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS, n8n_service
    n8n_service.invalidate_leads_cache()
    
    new_msg = {
        "id": f"msg_in_{int(datetime.utcnow().timestamp())}",
        "sender": sender,
        "message": message_text,
        "channel": "instagram",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if lead_id not in MOCK_CONVERSATIONS:
        MOCK_CONVERSATIONS[lead_id] = []
    MOCK_CONVERSATIONS[lead_id].append(new_msg)
    
    # Update last interaction timestamp on lead
    for lead in MOCK_LEADS:
        if lead["id"] == lead_id:
            lead["last_interaction"] = datetime.utcnow().isoformat() + "Z"
            if sender == "lead":
                lead["status"] = "RESPONDED"
            break
            
    # Notify listeners in real time
    await notify_lead_listeners(lead_id, "reload")
    await notify_crm_chat_listeners(lead_id)
            
    return {"status": "success", "message": new_msg}
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
    
    if event_type == "session.status" and status in ["STOPPED", "FAILED", "DISCONNECTED", "UNPAIRED", "TIMEOUT"]:
        # Broadcast to all CRM chat listeners that a session has disconnected
        msg = json.dumps({
            "action": "session_disconnected",
            "session_id": session_id,
            "status": status,
            "message": f"A sessão '{session_id}' foi desconectada."
        })
        for user_email, queue in list(crm_chat_listeners):
            await queue.put(msg)
            
    return {"status": "success"}

@router.post("/outbound/whatsapp/send")
async def n8n_outbound_whatsapp_send(
    payload: Dict[str, Any] = Body(...),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Endpoint para envio de mensagens via N8N ou ferramentas externas.
    O Dominus é responsável por gerar o JWT do Identity Provider e repassar à WhatsApp API.
    """
    master_key = x_master_api_key or payload.get("master_api_key") or payload.get("x_master_api_key")
    if not master_key or master_key != settings.WHATSAPP_MASTER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")

    session_id = payload.get("session_id", "default")
    phone = payload.get("phone") or payload.get("number")
    message = payload.get("message") or payload.get("text")
    
    if not phone:
        raise HTTPException(status_code=400, detail="Missing phone or number")

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    
    from app.api.endpoints.whatsapp import make_whatsapp_api_request
    from app.services.identity_service import get_m2m_jwt
    
    tenant_id = payload.get("tenant_id") or getattr(settings, "ADMIN_TENANT_ID", "admin") or "admin"
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
        "jid": f"{cleaned_phone}@s.whatsapp.net"
    }
    
    if message:
        json_data["message"] = message
        json_data["text"] = message
        
    for k, v in payload.items():
        if k not in ["phone", "number", "message", "text", "session_id", "tenant_id", "jid", "master_api_key", "x_master_api_key"]:
            json_data[k] = v
            
    res = await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers=headers,
        json_data=json_data
    )
    
    return JSONResponse(status_code=200, content=res)
