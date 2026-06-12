from fastapi import APIRouter, Depends, HTTPException
from app.schemas.scrape import ScrapePayload
from app.services.n8n_service import n8n_service
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/meta_ads")
async def run_scrape_meta_ads(payload: ScrapePayload, current_user: str = Depends(get_current_user)):
    """
    Trigger the Meta Ads scraper workflow on N8N.
    """
    result = await n8n_service.run_scrapper(payload.model_dump())
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Erro ao executar scraper de Meta Ads"))
    return result

@router.post("/google_maps")
async def run_scrape_google_maps(payload: ScrapePayload, current_user: str = Depends(get_current_user)):
    """
    Trigger the Google Maps scraper workflow on N8N.
    """
    result = await n8n_service.run_scrapper(payload.model_dump(), platform="google_maps")
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Erro ao executar scraper de Google Maps"))
    return result
