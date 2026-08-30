"""
Documentação do módulo config.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base config.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base config funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
import os
from dotenv import load_dotenv
if os.path.exists(".env.example"):
    load_dotenv(".env.example")
if os.path.exists(".env"):
    # Keep explicitly supplied environment variables authoritative. This lets
    # local/dev runners select SQLite and service endpoints without rewriting
    # the developer's .env file.
    load_dotenv(".env", override=False)

# Clean empty strings from os.environ so Pydantic defaults apply
for k, v in list(os.environ.items()):
    if v in ('""', "''", ""):
        del os.environ[k]

from pydantic_settings import BaseSettings
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    """
    Classe Settings.

    O que faz: Representa a estrutura de dados e operações para a entidade Settings em o módulo core/base config.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Settings, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    PROJECT_NAME: str = "Dominuslabs"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Authentication
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_TENANT_ID: str = os.getenv("ADMIN_TENANT_ID", os.getenv("MASTER_TENANT_ID", "admin"))
    VIEWER_USERNAME: str = os.getenv("VIEWER_USERNAME", "patrik182rodrigues@gmail.com")
    VIEWER_PASSWORD: str = os.getenv("VIEWER_PASSWORD", "")
    SECRET_KEY: str = os.getenv("JWT_SECRET", "")

    # LiteLLM TTS
    LITELLM_API_KEY: Optional[str] = os.getenv("LITELLM_API_KEY")
    LITELLM_API_BASE: Optional[str] = os.getenv("LITELLM_API_BASE")

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))

    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Database (SQLite file stored in persistent uploads directory or PostgreSQL if DATABASE_URL is set)
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Função/Método SQLALCHEMY_DATABASE_URI.

        O que faz: Processa SQLALCHEMY_DATABASE_URI sem parâmetros específicos no contexto de o módulo core/base config.
        Impacto na regra de negócio: Assegura que o fluxo da operação SQLALCHEMY_DATABASE_URI seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        if self.DATABASE_URL:
            # SQLAlchemy expects 'postgresql://' instead of 'postgres://'
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        return f"sqlite:///{os.path.join(self.UPLOAD_DIR, 'dominuslabs.db')}"

    # N8N Integration Webhooks
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
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
    ACCEPT_ORDER_WEBHOOK_URL: str = os.getenv("ACCEPT_ORDER_WEBHOOK_URL", "https://myn8n.seommerce.shop/webhook/accept_order")
    
    WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "http://localhost:3000")
    WHATSAPP_PUBLIC_URL: str = os.getenv("WHATSAPP_PUBLIC_URL", "https://dominuslabs.online")
    WHATSAPP_MASTER_SECRET: str = os.getenv("WHATSAPP_MASTER_SECRET", os.getenv("WHATSAPP_MASTER_KEY", os.getenv("MASTER_API_KEY", "")))
    IDENTITY_WORKER_URL: str = os.getenv("IDENTITY_WORKER_URL", "https://identity.dominus.online")

    # Hybrid Encryption Keys (Zero-Trust)
    DOMINUS_PRIVATE_KEY: str = os.getenv("DOMINUS_PRIVATE_KEY", "")
    DOMINUS_PUBLIC_KEY: str = os.getenv("DOMINUS_PUBLIC_KEY", "")
    WHATS_API_PUBLIC_KEY: str = os.getenv("WHATS_API_PUBLIC_KEY", "")
    IDPW_PUBLIC_KEY: str = os.getenv("IDPW_PUBLIC_KEY", "")
    N8N_PUBLIC_KEY: str = os.getenv("N8N_PUBLIC_KEY", "")

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o módulo core/base config.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        case_sensitive = True

settings = Settings()
