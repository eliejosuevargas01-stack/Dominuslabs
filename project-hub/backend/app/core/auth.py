import os
import base64
import json
import hmac
import hashlib
import time
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

SECRET_KEY = settings.SECRET_KEY
security = HTTPBearer()

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').replace('=', '')

def base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(data: dict, expires_in: int = 3600) -> str:
    """Create JWT token valid for 1 hour by default"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in
    
    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))
    
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        f"{header_b64}.{payload_b64}".encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def decode_access_token(token: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        
        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            f"{header_b64}.{payload_b64}".encode('utf-8'),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64url_encode(expected_sig)
        
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None
            
        payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
        if payload.get("exp", 0) < time.time():
            return None # Expired
            
        return payload
    except Exception:
        return None

def create_refresh_token(data: dict, expires_in: int = 604800) -> str:
    """Create a refresh token valid for 7 days (604800 seconds)"""
    payload = data.copy()
    payload["type"] = "refresh"
    return create_access_token(payload, expires_in=expires_in)

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido ou expirado"
        )
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=401,
            detail="Token de acesso inválido (enviado token de atualização)"
        )
    return payload.get("sub", "")

def check_admin_role(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido ou expirado"
        )
    email = payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: apenas administradores podem realizar esta operação"
        )
    return email

def user_has_permission(user: User, required_perm: str) -> bool:
    if not user:
        return False
    if user.role == "admin":
        return True
    if not user.permissions:
        return False
    perms = [p.strip().lower() for p in user.permissions.split(",")]
    return required_perm.lower() in perms or "*" in perms

def check_permission(required_perm: str, credentials: HTTPAuthorizationCredentials, db: Session) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado")
    email = payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=403, detail="Usuário não encontrado.")
    if not user_has_permission(user, required_perm):
        raise HTTPException(
            status_code=403,
            detail=f"Acesso negado: você não possui a permissão '{required_perm}' necessária."
        )
    return email

def check_read_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("read", credentials, db)

def check_write_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("write", credentials, db)

def check_update_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("update", credentials, db)

def check_delete_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("delete", credentials, db)

# Compatibility aliases for existing endpoint dependencies
def check_project_create_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_write_permission(credentials, db)

def check_project_edit_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_update_permission(credentials, db)

def check_crm_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_read_permission(credentials, db)

def check_scrapper_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_write_permission(credentials, db)
