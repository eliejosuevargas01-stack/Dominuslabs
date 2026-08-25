import os
from dotenv import load_dotenv

if os.path.exists(".env.example"):
    load_dotenv(".env.example")
if os.path.exists(".env"):
    load_dotenv(".env", override=True)

# Clean empty strings from os.environ so Pydantic defaults apply
for k, v in list(os.environ.items()):
    if v in ('""', "''", ""):
        del os.environ[k]

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
    ADMIN_TENANT_ID: str = os.getenv("ADMIN_TENANT_ID", os.getenv("MASTER_TENANT_ID", "admin"))
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
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "default_webhook_secret")
    SCRAPPER_META_WEBHOOK_URL: str = os.getenv("SCRAPPER_META_WEBHOOK_URL", "https://scrapper.dominuslabs.online/scrape/meta_ads")
    SCRAPPER_MAPS_WEBHOOK_URL: str = os.getenv("SCRAPPER_MAPS_WEBHOOK_URL", "https://scrapper.dominuslabs.online/scrape/google_maps")
    CRM_GET_LEADS_WEBHOOK_URL: str = os.getenv("CRM_GET_LEADS_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_CREATE_LEAD_WEBHOOK_URL: str = os.getenv("CRM_CREATE_LEAD_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_UPDATE_LEAD_WEBHOOK_URL: str = os.getenv("CRM_UPDATE_LEAD_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_DELETE_LEAD_WEBHOOK_URL: str = os.getenv("CRM_DELETE_LEAD_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_GET_MESSAGES_WEBHOOK_URL: str = os.getenv("CRM_GET_MESSAGES_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_CREATE_MESSAGE_WEBHOOK_URL: str = os.getenv("CRM_CREATE_MESSAGE_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_SEND_WHATSAPP_WEBHOOK_URL: str = os.getenv("CRM_SEND_WHATSAPP_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_UPDATE_STATUS_WEBHOOK_URL: str = os.getenv("CRM_UPDATE_STATUS_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    CRM_CREATE_ACTIVITY_WEBHOOK_URL: str = os.getenv("CRM_CREATE_ACTIVITY_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/crm")
    
    WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "http://localhost:3000")
    WHATSAPP_PUBLIC_URL: str = os.getenv("WHATSAPP_PUBLIC_URL", "https://dominuslabs.online")
    WHATSAPP_MASTER_SECRET: str = os.getenv("WHATSAPP_MASTER_SECRET", os.getenv("WHATSAPP_MASTER_KEY", os.getenv("MASTER_API_KEY", "default_master_secret")))
    IDENTITY_WORKER_URL: str = os.getenv("IDENTITY_WORKER_URL", "https://identity.dominus.online")

    # Hybrid Encryption Keys (Zero-Trust)
    DOMINUS_PRIVATE_KEY: str = os.getenv("DOMINUS_PRIVATE_KEY", "")
    DOMINUS_PUBLIC_KEY: str = os.getenv("DOMINUS_PUBLIC_KEY", "")
    WHATS_API_PUBLIC_KEY: str = os.getenv("WHATS_API_PUBLIC_KEY", "")
    IDPW_PUBLIC_KEY: str = os.getenv("IDPW_PUBLIC_KEY", "")
    N8N_PUBLIC_KEY: str = os.getenv("N8N_PUBLIC_KEY", "")

    class Config:
        case_sensitive = True

settings = Settings()