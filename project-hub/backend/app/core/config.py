import os
from dotenv import load_dotenv

load_dotenv()

from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Dominuslabs"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Authentication
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")
    VIEWER_USERNAME: str = os.getenv("VIEWER_USERNAME", "patrik182rodrigues@gmail.com")
    VIEWER_PASSWORD: str = os.getenv("VIEWER_PASSWORD", "patrik182")
    SECRET_KEY: str = os.getenv("JWT_SECRET", "dominuslabs-super-secret-key-2026")

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))

    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Database (SQLite file stored in persistent uploads directory or PostgreSQL if DATABASE_URL is set)
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            # SQLAlchemy expects 'postgresql://' instead of 'postgres://'
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        return f"sqlite:///{os.path.join(self.UPLOAD_DIR, 'dominuslabs.db')}"

    # N8N Integration Webhooks
    SCRAPPER_META_WEBHOOK_URL: str = os.getenv("SCRAPPER_META_WEBHOOK_URL", "https://scrapper.dominuslabs.online/scrape/meta_ads")
    SCRAPPER_MAPS_WEBHOOK_URL: str = os.getenv("SCRAPPER_MAPS_WEBHOOK_URL", "https://scrapper.dominuslabs.online/scrape/google_maps")
    CRM_GET_LEADS_WEBHOOK_URL: str = os.getenv("CRM_GET_LEADS_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_CREATE_LEAD_WEBHOOK_URL: str = os.getenv("CRM_CREATE_LEAD_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_UPDATE_LEAD_WEBHOOK_URL: str = os.getenv("CRM_UPDATE_LEAD_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_DELETE_LEAD_WEBHOOK_URL: str = os.getenv("CRM_DELETE_LEAD_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_GET_MESSAGES_WEBHOOK_URL: str = os.getenv("CRM_GET_MESSAGES_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_CREATE_MESSAGE_WEBHOOK_URL: str = os.getenv("CRM_CREATE_MESSAGE_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_SEND_WHATSAPP_WEBHOOK_URL: str = os.getenv("CRM_SEND_WHATSAPP_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/lead_messages_sent")
    CRM_UPDATE_STATUS_WEBHOOK_URL: str = os.getenv("CRM_UPDATE_STATUS_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_CREATE_ACTIVITY_WEBHOOK_URL: str = os.getenv("CRM_CREATE_ACTIVITY_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    
    WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "http://localhost:3000")

    class Config:
        case_sensitive = True

settings = Settings()