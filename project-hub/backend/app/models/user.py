from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="custom", nullable=False)  # "admin" or "custom"
    
    # Permission flags
    can_create_projects = Column(Boolean, default=False, nullable=False)
    can_edit_projects = Column(Boolean, default=False, nullable=False)
    can_manage_crm = Column(Boolean, default=True, nullable=False)
    can_use_scrapper = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
