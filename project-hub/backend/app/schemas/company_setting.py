from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class MenuItemSchema(BaseModel):
    id: Optional[str] = None
    name: str
    category: Optional[str] = None
    price: Optional[float] = 0.0
    description: Optional[str] = None
    available: Optional[bool] = True
    image_url: Optional[str] = None

class CompanySettingBase(BaseModel):
    company_name: Optional[str] = None
    niche: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    address_number: Optional[str] = None
    address_neighborhood: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    business_hours: Optional[str] = None

    tone_of_voice: Optional[str] = None
    custom_instructions: Optional[str] = None

    exchange_policy: Optional[str] = None
    delivery_policy: Optional[str] = None
    terms_of_service: Optional[str] = None

    menu_catalog: Optional[List[Dict[str, Any]]] = []
    accepted_payment_types: Optional[List[str]] = []
    payment_notes: Optional[str] = None

    values_mission: Optional[str] = None
    additional_notes: Optional[str] = None

    delivery_fee_type: Optional[str] = None
    delivery_fee_value: Optional[float] = None
    delivery_radius_km: Optional[float] = None
    delivery_max_coverage_km: Optional[float] = 20.0
    delivery_tiers: Optional[List[Dict[str, Any]]] = []
    minimum_order_value: Optional[float] = None
    preparation_time_minutes: Optional[int] = None
    
    promotions: Optional[List[Dict[str, Any]]] = []

class CompanySettingCreate(CompanySettingBase):
    tenant_id: Optional[str] = "default"

class CompanySettingUpdate(CompanySettingBase):
    pass

class CompanySettingResponse(CompanySettingBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
