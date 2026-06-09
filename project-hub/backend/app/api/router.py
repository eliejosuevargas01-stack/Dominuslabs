from fastapi import APIRouter

from app.api.endpoints import projects, uploads, webhooks

api_router = APIRouter()

api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])