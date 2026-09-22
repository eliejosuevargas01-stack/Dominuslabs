"""FastAPI router para o módulo Pedidos10."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.models.tenant_platform_integration import TenantPlatformIntegration
from app.pedidos10.manager import pedidos10_manager
from app.pedidos10.auth_manager import AuthManager
from app.pedidos10.schemas import (
    Pedidos10Credentials,
    Pedidos10Session,
    CatalogItem,
    OrderItem,
)

router = APIRouter(prefix="/pedidos10", tags=["Pedidos10"])
security = HTTPBearer()


@router.post("/connect")
async def connect(
    credentials: Pedidos10Credentials,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """
    Registra credenciais + inicia bridge para tenant.
    Credenciais são criptografadas via credential_vault.
    """
    auth_manager = AuthManager()

    # Testa login primeiro
    try:
        session = await auth_manager.login(credentials)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Criptografa e salva
    credentials_enc = await auth_manager.store_credentials(credentials.email, credentials.password)

    # Salva no DB
    integration = TenantPlatformIntegration(
        tenant_id=user.tenant_id,
        platform="pedidos10",
        display_name=f"Pedidos10 - {user.email}",
        credentials_enc=credentials_enc,
        base_url="https://api-monitor.pedidos10.com.br/api-gestor-V1",
        auth_url="https://api-monitor.pedidos10.com.br/api-gestor-V1/auth",
        is_active=True,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    # Inicia bridge
    await pedidos10_manager.start_integration(
        integration_id=str(integration.id),
        db=db,
        tenant_id=user.tenant_id,
        credentials_enc=credentials_enc,
    )

    return {"message": "Connected successfully", "integration_id": str(integration.id)}


@router.delete("/disconnect/{integration_id}")
async def disconnect(
    integration_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Para bridge e remove integração."""
    integration = db.query(TenantPlatformIntegration).filter(
        TenantPlatformIntegration.id == integration_id,
        TenantPlatformIntegration.tenant_id == user.tenant_id
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    await pedidos10_manager.stop_integration(integration_id)
    db.delete(integration)
    db.commit()

    return {"message": "Disconnected successfully"}


@router.get("/status")
async def get_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Lista status de todas as bridges do tenant."""
    return pedidos10_manager.get_all_statuses()


@router.get("/status/{integration_id}")
async def get_status_single(
    integration_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Status específico de uma integration."""
    status = pedidos10_manager.get_status(integration_id)
    if not status:
        raise HTTPException(status_code=404, detail="Integration not found")
    return status


@router.post("/refresh/{integration_id}")
async def refresh(
    integration_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Força reauth manual."""
    integration = db.query(TenantPlatformIntegration).filter(
        TenantPlatformIntegration.id == integration_id,
        TenantPlatformIntegration.tenant_id == user.tenant_id
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        await pedidos10_manager.restart_integration(
            integration_id=integration_id,
            db=db,
            tenant_id=user.tenant_id,
            credentials_enc=integration.credentials_enc,
        )
        return {"message": "Refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/{integration_id}")
async def get_catalog(
    integration_id: str,
    merchant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Busca catálogo atual da loja (polling fallback)."""
    bridge = pedidos10_manager._bridges.get(integration_id)
    if not bridge:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Se não tiver merchant_id, busca do user_info
    if not merchant_id and bridge._session:
        user_info = await bridge.auth_manager.get_user_info(bridge._session)
        if user_info.merchants:
            merchant_id = user_info.merchants[0].get("id_merchant")

    if not merchant_id:
        raise HTTPException(status_code=400, detail="merchant_id not provided")

    catalog = await bridge.get_catalog(merchant_id)
    return {"merchant_id": merchant_id, "catalog": catalog}


@router.get("/orders/{integration_id}")
async def get_orders(
    integration_id: str,
    merchant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Busca pedidos atuais (polling fallback)."""
    bridge = pedidos10_manager._bridges.get(integration_id)
    if not bridge:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Se não tiver merchant_id, busca do user_info
    if not merchant_id and bridge._session:
        user_info = await bridge.auth_manager.get_user_info(bridge._session)
        if user_info.merchants:
            merchant_id = user_info.merchants[0].get("id_merchant")

    if not merchant_id:
        raise HTTPException(status_code=400, detail="merchant_id not provided")

    orders = await bridge.get_pending_orders(merchant_id)
    return {"merchant_id": merchant_id, "orders": orders}


@router.post("/test-connection")
async def test_connection(
    credentials: Pedidos10Credentials,
    user: User = Depends(get_current_active_user),
):
    """Testa credenciais sem persistir."""
    auth_manager = AuthManager()
    try:
        session = await auth_manager.login(credentials)
        return {"message": "Connection successful", "jwt_token": session.jwt[:20] + "..."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
