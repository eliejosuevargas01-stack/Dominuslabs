from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.core.database import get_db
from app.services.webhook_service import webhook_service

router = APIRouter()

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
                # GitHub dates can end in 'Z' or offset, replace Z with offset for compatibility
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