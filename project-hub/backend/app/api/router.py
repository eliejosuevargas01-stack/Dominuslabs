from fastapi import APIRouter

from app.api.endpoints import projects, uploads, webhooks, auth, scrapper, crm, scrape

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(scrapper.router, prefix="/scrapper", tags=["scrapper"])
api_router.include_router(crm.router, prefix="/crm", tags=["crm"])
api_router.include_router(scrape.router, prefix="/scrape", tags=["scrape"])