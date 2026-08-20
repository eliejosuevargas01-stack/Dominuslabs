from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None
    price: Optional[float] = 0.0
    description: Optional[str] = None
    available: Optional[bool] = True
    image_url: Optional[str] = None
    stock: Optional[int] = 0

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    available: Optional[bool] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None

class ProductResponse(ProductBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        orm_mode = True
