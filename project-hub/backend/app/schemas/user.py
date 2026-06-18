from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str
    role: str = "custom"
    can_create_projects: bool = False
    can_edit_projects: bool = False
    can_manage_crm: bool = True
    can_use_scrapper: bool = True
    whatsapp_token: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    can_create_projects: Optional[bool] = None
    can_edit_projects: Optional[bool] = None
    can_manage_crm: Optional[bool] = None
    can_use_scrapper: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
