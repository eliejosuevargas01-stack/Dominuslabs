import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class TenantPlatformIntegration(Base):
    __tablename__ = "tenant_platform_integrations"
    
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(String(255), nullable=False, index=True)
    platform        = Column(String(64), nullable=False)         # "pedidos10", "ifood"
    display_name    = Column(String(255), nullable=True)         # "Pedidos10 - Loja Centro"
    credentials_enc = Column(Text, nullable=False)               # JSON encriptado
    app_id          = Column(String(255), nullable=True)
    merchant_id     = Column(String(255), nullable=True)
    base_url        = Column(String(512), nullable=False)
    auth_url        = Column(String(512), nullable=True)
    webhook_secret  = Column(Text, nullable=True)                # encriptado
    is_active       = Column(Boolean, default=True, index=True)
    last_sync_at    = Column(DateTime, nullable=True)
    last_error      = Column(Text, nullable=True)
    store_code      = Column(String(255), nullable=True)
    onboarding_status = Column(String(32), default="pending")
    created_at      = Column(DateTime, default=utc_now)
    updated_at      = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "platform", "merchant_id", name="uq_tenant_platform_merchant"),
    )
