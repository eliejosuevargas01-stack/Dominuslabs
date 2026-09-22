"""Integrações de plataformas endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.tenant_platform_integration import TenantPlatformIntegration
from app.core.credential_vault import encrypt_credentials

router = APIRouter()

# Plataformas whitelist com URLs
PLATFORM_CONFIG = {
    "pedidos10": {
        "base_url": "https://api.pedidos10.com.br",
        "auth_url": "https://auth.pedidos10.com.br"
    },
    "ifood": {
        "base_url": "https://merchant-api.ifood.com.br",
        "auth_url": "https://merchant-api.ifood.com.br/authentication"
    },
    "aiqfome": {
        "base_url": "https://api.aiqfome.com",
        "auth_url": "https://api.aiqfome.com"
    }
}


class IntegrationCreate(BaseModel):
    platform: str
    store_code: str
    display_name: Optional[str] = None


class IntegrationPatch(BaseModel):
    is_active: bool


def _serialize_integration(intg: TenantPlatformIntegration) -> dict:
    """Serializa integração SEM credentials_enc."""
    return {
        "id": str(intg.id),
        "platform": intg.platform,
        "display_name": intg.display_name,
        "is_active": intg.is_active,
        "onboarding_status": intg.onboarding_status,
        "last_sync_at": intg.last_sync_at.isoformat() if intg.last_sync_at else None,
        "last_error": intg.last_error,
        "merchant_id": intg.merchant_id,
        "store_code": intg.store_code,
    }


def _get_user_and_tenant(db: Session, current_user: str):
    """Busca usuário pelo email do JWT e retorna (user, tenant_id)."""
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant_id associado")
    return user, tenant_id


def _get_integration(db: Session, integration_id: str, tenant_id: str) -> TenantPlatformIntegration:
    """Busca integração verificando ownership pelo tenant_id."""
    intg = db.query(TenantPlatformIntegration).filter(
        TenantPlatformIntegration.id == integration_id,
        TenantPlatformIntegration.tenant_id == tenant_id
    ).first()
    if not intg:
        raise HTTPException(status_code=404, detail="Integração não encontrada")
    return intg


@router.get("", response_model=List[dict])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Lista integrações do tenant."""
    _, tenant_id = _get_user_and_tenant(db, current_user)
    integrations = db.query(TenantPlatformIntegration).filter(
        TenantPlatformIntegration.tenant_id == tenant_id
    ).all()
    return [_serialize_integration(i) for i in integrations]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_integration(
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Cria nova integração."""
    _, tenant_id = _get_user_and_tenant(db, current_user)

    if payload.platform not in PLATFORM_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plataforma não suportada. Opções: {list(PLATFORM_CONFIG.keys())}"
        )
    if not payload.store_code or not payload.store_code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="store_code não pode ser vazio"
        )

    # Verifica duplicidade ativa para mesmo platform+tenant
    existing = db.query(TenantPlatformIntegration).filter(
        TenantPlatformIntegration.tenant_id == tenant_id,
        TenantPlatformIntegration.platform == payload.platform,
        TenantPlatformIntegration.is_active == True
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma integração ativa para a plataforma {payload.platform}"
        )

    # Credenciais MVP
    credentials = {
        "clientId": payload.store_code,
        "clientSecret": "pending_oauth"
    }
    credentials_enc = encrypt_credentials(credentials)
    config = PLATFORM_CONFIG[payload.platform]

    new_integration = TenantPlatformIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        platform=payload.platform,
        display_name=payload.display_name or f"{payload.platform.capitalize()} - {payload.store_code}",
        credentials_enc=credentials_enc,
        merchant_id=payload.store_code,
        base_url=config["base_url"],
        auth_url=config["auth_url"],
        is_active=True,
        onboarding_status="active",
        store_code=payload.store_code
    )

    db.add(new_integration)
    db.commit()
    db.refresh(new_integration)

    return _serialize_integration(new_integration)


@router.delete("/{integration_id}", status_code=status.HTTP_200_OK)
def delete_integration(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Soft-delete de integração."""
    _, tenant_id = _get_user_and_tenant(db, current_user)
    integration = _get_integration(db, integration_id, tenant_id)

    integration.is_active = False
    integration.credentials_enc = ""
    db.commit()
    return {"ok": True}


@router.patch("/{integration_id}", status_code=status.HTTP_200_OK)
def patch_integration(
    integration_id: str,
    payload: IntegrationPatch,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Ativar ou desativar integração."""
    _, tenant_id = _get_user_and_tenant(db, current_user)
    integration = _get_integration(db, integration_id, tenant_id)

    integration.is_active = payload.is_active
    db.commit()
    return {"id": str(integration.id), "is_active": integration.is_active}