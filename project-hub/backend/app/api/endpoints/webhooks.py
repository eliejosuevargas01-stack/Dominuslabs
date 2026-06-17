from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
import asyncio

from app.core.database import get_db
from app.services.webhook_service import webhook_service

router = APIRouter()

from pydantic import BaseModel

class LeadChatUpdateRequest(BaseModel):
    lead_id: str

# In-memory queues for Server-Sent Events (SSE)
project_listeners = {}  # {public_token: [asyncio.Queue]}
global_listeners = []   # [asyncio.Queue]
lead_listeners = {}     # {lead_id: [(user_email, queue)]}

async def notify_lead_listeners(lead_id: str, event: str = "reload"):
    if lead_id in lead_listeners:
        for user_email, queue in list(lead_listeners[lead_id]):
            await queue.put(event)

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
                # Remove current queue tuple
                lead_listeners[lead_id] = [item for item in lead_listeners[lead_id] if item[1] != queue]
                if not lead_listeners[lead_id]:
                    del lead_listeners[lead_id]
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/crm/update-chat")
async def update_chat_webhook_post(request: Request, lead_id: str = None):
    resolved_lead_id = lead_id
    if not resolved_lead_id:
        try:
            body = await request.json()
            resolved_lead_id = body.get("lead_id")
        except Exception:
            pass
            
    if not resolved_lead_id:
        raise HTTPException(status_code=400, detail="Missing lead_id parameter")
    
    # Check if there are active listeners for this lead
    if resolved_lead_id not in lead_listeners or not lead_listeners[resolved_lead_id]:
        return {
            "status": "ignored",
            "reason": f"No active listeners for lead {resolved_lead_id}"
        }
    
    from app.services.n8n_service import n8n_service
    # Fetch messages to update cache/db
    await n8n_service.get_messages(resolved_lead_id)
    
    # Notify listeners to reload chat
    await notify_lead_listeners(resolved_lead_id, "reload")
    
    return {
        "status": "success",
        "notified_sessions": len(lead_listeners[resolved_lead_id])
    }

@router.get("/crm/update-chat")
async def update_chat_webhook_get(lead_id: str):
    if not lead_id:
        raise HTTPException(status_code=400, detail="Missing lead_id parameter")
        
    # Check if there are active listeners for this lead
    if lead_id not in lead_listeners or not lead_listeners[lead_id]:
        return {
            "status": "ignored",
            "reason": f"No active listeners for lead {lead_id}"
        }
    
    from app.services.n8n_service import n8n_service
    # Fetch messages to update cache/db
    await n8n_service.get_messages(lead_id)
    
    # Notify listeners to reload chat
    await notify_lead_listeners(lead_id, "reload")
    
    return {
        "status": "success",
        "notified_sessions": len(lead_listeners[lead_id])
    }

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
    payload = await request.json()
    lead_id = payload.get("lead_id")
    message_text = payload.get("message")
    sender = payload.get("sender", "lead")
    
    if not lead_id or not message_text:
        return {"status": "ignored", "reason": "missing lead_id or message"}
        
    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS
    
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
            
    return {"status": "success", "message": new_msg}

@router.post("/inbound/instagram")
async def instagram_inbound_webhook(request: Request):
    """
    Inbound webhook for Instagram messages.
    Receives message payload and appends to in-memory conversation list.
    """
    payload = await request.json()
    lead_id = payload.get("lead_id")
    message_text = payload.get("message")
    sender = payload.get("sender", "lead")
    
    if not lead_id or not message_text:
        return {"status": "ignored", "reason": "missing lead_id or message"}
        
    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS
    
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
            
    return {"status": "success", "message": new_msg}