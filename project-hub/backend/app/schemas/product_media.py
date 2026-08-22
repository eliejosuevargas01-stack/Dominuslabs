from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductMediaBase(BaseModel):
    product_id: str
    media_type: str
    media_url: str

class ProductMediaCreate(ProductMediaBase):
    tenant_id: Optional[str] = "default"

class ProductMediaResponse(ProductMediaBase):
    id: int
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True
