from fastapi import APIRouter, Depends, HTTPException
from app.schemas.scrapper import ScrapperRunPayload
from app.services.n8n_service import n8n_service
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/run")
async def run_scrapper(payload: ScrapperRunPayload, current_user: str = Depends(get_current_user)):
    """
    Trigger the scraper search workflow on N8N.
    This routes to the SCRAPPER_WEBHOOK_URL.
    """
    result = await n8n_service.run_scrapper(payload.model_dump())
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Erro ao executar busca no N8N"))
    return result
