from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.services.webhook_service import webhook_service

router = APIRouter()

@router.post("/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    # In a real app, verify signature and parse payload.
    # We are simulating parsing the expected fields.
    payload = await request.json()

    project_id = payload.get("project_id")
    commit_hash = payload.get("commit_hash")
    message = payload.get("commit_message")
    author = payload.get("author")
    date_str = payload.get("date")

    if not all([project_id, commit_hash, message, author, date_str]):
        # Just return 200 for now if structure is wrong, as this is a stub
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