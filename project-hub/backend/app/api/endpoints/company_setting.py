"""
Documentação do módulo company_setting.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para company_setting.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para company_setting funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.company_setting import CompanySettingResponse, CompanySettingUpdate
from app.repositories.company_setting_repo import company_setting_repo
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=CompanySettingResponse)
def get_company_settings(
    tenant_id: str = "default",
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Retrieve company settings for a given tenant."""
    return company_setting_repo.get_by_tenant(db, tenant_id=tenant_id)

@router.put("/", response_model=CompanySettingResponse)
def update_company_settings(
    setting_in: CompanySettingUpdate,
    tenant_id: str = "default",
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Update or upsert company settings for a given tenant."""
    return company_setting_repo.upsert(db, obj_in=setting_in, tenant_id=tenant_id)
