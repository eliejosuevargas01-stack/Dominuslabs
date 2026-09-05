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
from app.core.auth import get_current_active_user, resolve_tenant_from_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=CompanySettingResponse)
def get_company_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve company settings for the authenticated tenant."""
    tenant_id = resolve_tenant_from_user(current_user)
    return company_setting_repo.get_by_tenant(db, tenant_id=tenant_id)

@router.put("/", response_model=CompanySettingResponse)
def update_company_settings(
    setting_in: CompanySettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update or upsert company settings for the authenticated tenant."""
    tenant_id = resolve_tenant_from_user(current_user)
    return company_setting_repo.upsert(db, obj_in=setting_in, tenant_id=tenant_id)
