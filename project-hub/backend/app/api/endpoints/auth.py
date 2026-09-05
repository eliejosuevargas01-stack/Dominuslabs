"""
Módulo principal de Autenticação.
Controla o fluxo de login dos usuários corporativos via token JWT local e também engatilha provisionamentos invisíveis na infraestrutura do provedor oficial de WhatsApp, integrando a segurança M2M do ecossistema.
"""
import secrets
import httpx
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.database import get_db
from app.models.user import User
from app.core.security import verify_password
from app.core.auth import create_access_token, create_refresh_token, decode_access_token


logger = logging.getLogger("auth")
router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_token_data(user: User) -> dict:
    role = getattr(user, "role", "custom") or "custom"
    perms = getattr(user, "permissions", "") or "read,write,update,delete"
    is_admin = role == "admin"
    tenant_id = getattr(user, "tenant_id", None)
    if not tenant_id:
        tenant_id = settings.ADMIN_TENANT_ID if is_admin else "default"
    return {
        "sub": user.email,
        "role": role,
        "can_create_projects": getattr(user, "can_create_projects", None) if getattr(user, "can_create_projects", None) is not None else (is_admin or "write" in perms),
        "can_edit_projects": getattr(user, "can_edit_projects", None) if getattr(user, "can_edit_projects", None) is not None else (is_admin or "write" in perms),
        "can_manage_crm": getattr(user, "can_manage_crm", None) if getattr(user, "can_manage_crm", None) is not None else True,
        "can_use_scrapper": getattr(user, "can_use_scrapper", None) if getattr(user, "can_use_scrapper", None) is not None else True,
        "tenant_id": tenant_id,
    }


from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    username = payload.username
    if "@" not in username:
        username = f"{username}@dominuslabs.online"
    if username.lower() in ("eliejousuevargas01@gmail.com", "eliejousuevargas01@dominuslabs.online"):
        username = "Eliejosuevargas01@gmail.com"

    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.error("[FLOW-STEP 1] ERROR: User login failed")
        print("[FLOW-STEP 1] ERROR: User login failed", flush=True)
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

    logger.info("[FLOW-STEP 1] User logged in successfully")
    print("[FLOW-STEP 1] User logged in successfully", flush=True)

    # Garante whatsapp_token local
    if not user.whatsapp_token:
        user.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"

    token_data = _build_token_data(user)
    access_token = create_access_token(data=token_data, expires_in=3600)
    refresh_token = create_refresh_token(data=token_data, expires_in=604800)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.access_token = access_token
    user.refresh_token = refresh_token
    user.token_issued_at = now
    user.token_expires_at = now + timedelta(seconds=3600)
    db.commit()
    db.refresh(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "reauth_at_seconds": 3599,
        "whatsapp_token": user.whatsapp_token,
    }


@router.post("/refresh")
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    token_payload = decode_access_token(payload.refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de atualização inválido ou expirado")

    email = token_payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    if not user.whatsapp_token:
        user.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"

    token_data = _build_token_data(user)
    new_access_token = create_access_token(data=token_data, expires_in=3600)
    new_refresh_token = create_refresh_token(data=token_data, expires_in=604800)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.access_token = new_access_token
    user.refresh_token = new_refresh_token
    user.token_issued_at = now
    user.token_expires_at = now + timedelta(seconds=3600)
    db.commit()
    db.refresh(user)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "reauth_at_seconds": 3599,
        "whatsapp_token": user.whatsapp_token,
    }
