"""
Documentação do módulo auth.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base auth.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base auth funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
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
    """
    Função/Método base64url_encode.

    O que faz: Processa base64url_encode recebendo os parâmetros (data) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação base64url_encode seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return base64.urlsafe_b64encode(data).decode('utf-8').replace('=', '')

def base64url_decode(data: str) -> bytes:
    """
    Função/Método base64url_decode.

    O que faz: Processa base64url_decode recebendo os parâmetros (data) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação base64url_decode seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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
    """
    Função/Método decode_access_token.

    O que faz: Processa decode_access_token recebendo os parâmetros (token) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação decode_access_token seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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
        raise HTTPException(status_code=401, detail="Token de acesso inválido ou expirado.")
    if payload.get("type") == "refresh":
        raise HTTPException(status_code=401, detail="Token de acesso inválido (enviado token de atualização)")
    return payload.get("sub", "")

def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de acesso inválido ou expirado.")
    if payload.get("type") == "refresh":
        raise HTTPException(status_code=401, detail="Token de acesso inválido (enviado token de atualização)")
    email = payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    return user

def resolve_tenant_from_user(user: User) -> str:
    tenant_id = getattr(user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: tenant_id não configurado para este usuário."
        )
    return tenant_id

def check_admin_role(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de acesso inválido ou expirado.")
    email = payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado: apenas administradores podem realizar esta operação")
    return email

def user_has_permission(user: User, required_perm: str) -> bool:
    """
    Função/Método user_has_permission.

    O que faz: Processa user_has_permission recebendo os parâmetros (user, required_perm) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação user_has_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    if not user:
        return False
    if user.role == "admin":
        return True
    if not user.permissions:
        return False
    perms = [p.strip().lower() for p in user.permissions.split(",")]
    if required_perm.lower() in perms or "*" in perms:
        return True
    
    # Suporte a compatibilidade e granularidade
    aliases = {
        "product.read": ["read"],
        "product.create": ["write"],
        "product.update": ["update"],
        "product.delete": ["delete"],
    }
    for alias in aliases.get(required_perm.lower(), []):
        if alias in perms:
            return True
    return False

def check_permission(required_perm: str, credentials: HTTPAuthorizationCredentials, db: Session) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de acesso inválido ou expirado.")
    email = payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=403, detail="Usuário não encontrado.")
    if not user_has_permission(user, required_perm):
        raise HTTPException(status_code=403, detail=f"Acesso negado: você não possui a permissão {required_perm} necessária.")
    return email

def check_read_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_read_permission.

    O que faz: Processa check_read_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_read_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_permission("read", credentials, db)

def check_write_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_write_permission.

    O que faz: Processa check_write_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_write_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_permission("write", credentials, db)

def check_update_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_update_permission.

    O que faz: Processa check_update_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_update_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_permission("update", credentials, db)

def check_delete_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_delete_permission.

    O que faz: Processa check_delete_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_delete_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_permission("delete", credentials, db)

def check_product_read_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("product.read", credentials, db)

def check_product_create_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("product.create", credentials, db)

def check_product_update_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("product.update", credentials, db)

def check_product_delete_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    return check_permission("product.delete", credentials, db)

# Compatibility aliases for existing endpoint dependencies
def check_project_create_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_project_create_permission.

    O que faz: Processa check_project_create_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_project_create_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_write_permission(credentials, db)

def check_project_edit_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_project_edit_permission.

    O que faz: Processa check_project_edit_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_project_edit_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_update_permission(credentials, db)

def check_crm_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_crm_permission.

    O que faz: Processa check_crm_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_crm_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_read_permission(credentials, db)

def check_scrapper_permission(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_scrapper_permission.

    O que faz: Processa check_scrapper_permission recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_scrapper_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return check_write_permission(credentials, db)
