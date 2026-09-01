"""
Documentação do módulo company_setting.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic company_setting.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic company_setting funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class MenuItemSchema(BaseModel):
    """
    Classe MenuItemSchema.

    O que faz: Representa a estrutura de dados e operações para a entidade MenuItemSchema em o esquema de validação Pydantic company_setting.
    Impacto na regra de negócio: Centraliza o comportamento da entidade MenuItemSchema, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: Optional[str] = None
    name: str
    category: Optional[str] = None
    price: Optional[float] = 0.0
    description: Optional[str] = None
    available: Optional[bool] = True
    image_url: Optional[str] = None

class CompanySettingBase(BaseModel):
    """
    Classe CompanySettingBase.

    O que faz: Representa a estrutura de dados e operações para a entidade CompanySettingBase em o esquema de validação Pydantic company_setting.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CompanySettingBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
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

    accepted_payment_types: Optional[List[str]] = []
    payment_notes: Optional[str] = None

    menu_catalog: Optional[List[Dict[str, Any]]] = []

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
    """
    Classe CompanySettingCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade CompanySettingCreate em o esquema de validação Pydantic company_setting.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CompanySettingCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    tenant_id: Optional[str] = "default"

class CompanySettingUpdate(CompanySettingBase):
    """
    Classe CompanySettingUpdate.

    O que faz: Representa a estrutura de dados e operações para a entidade CompanySettingUpdate em o esquema de validação Pydantic company_setting.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CompanySettingUpdate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    pass

class CompanySettingResponse(CompanySettingBase):
    """
    Classe CompanySettingResponse.

    O que faz: Representa a estrutura de dados e operações para a entidade CompanySettingResponse em o esquema de validação Pydantic company_setting.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CompanySettingResponse, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic company_setting.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True
