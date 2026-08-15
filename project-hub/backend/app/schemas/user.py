from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str
    role: str = "custom"
    permissions: str = "read"
    tenant_id: Optional[str] = None
    whatsapp_token: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
