from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tenant_id = Column(String, index=True, nullable=True)
    role = Column(String, default="custom", nullable=False)  # "admin" or "custom"
    
    # Permissions string (e.g., "read,write,update,delete")
    permissions = Column(String, default="read", nullable=False)
    
    can_create_projects = Column(Boolean, nullable=True, default=True)
    can_edit_projects = Column(Boolean, nullable=True, default=True)
    can_manage_crm = Column(Boolean, nullable=True, default=True)
    can_use_scrapper = Column(Boolean, nullable=True, default=True)
    
    whatsapp_token = Column(String, unique=True, nullable=True)
    preferred_session_id = Column(String, nullable=True)
    
    # Preventive 1h Token storage and expiration tracking
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    token_issued_at = Column(DateTime, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
