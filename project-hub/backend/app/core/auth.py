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
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        parts = token.split('.')
# Lógica de decisão (if): Avalia 'if len(parts) != 3:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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
        
# Lógica de decisão (if): Avalia 'if not hmac.compare_digest(sig...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None
            
        payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
# Lógica de decisão (if): Avalia 'if payload.get("exp", 0) < tim...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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
    """
    Função/Método get_current_user.

    O que faz: Recuperação de dados cadastrados para get_current_user recebendo os parâmetros (credentials) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_current_user seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
# Lógica de decisão (if): Avalia 'if not payload:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido ou expirado"
        )
# Lógica de decisão (if): Avalia 'if payload.get("type") == "ref...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=401,
            detail="Token de acesso inválido (enviado token de atualização)"
        )
    return payload.get("sub", "")

def check_admin_role(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> str:
    """
    Função/Método check_admin_role.

    O que faz: Processa check_admin_role recebendo os parâmetros (credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_admin_role seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
# Lógica de decisão (if): Avalia 'if not payload:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido ou expirado"
        )
    email = payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
# Lógica de decisão (if): Avalia 'if not user or user.role != "a...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: apenas administradores podem realizar esta operação"
        )
    return email

def user_has_permission(user: User, required_perm: str) -> bool:
    """
    Função/Método user_has_permission.

    O que faz: Processa user_has_permission recebendo os parâmetros (user, required_perm) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação user_has_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
# Lógica de decisão (if): Avalia 'if not user:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not user:
        return False
# Lógica de decisão (if): Avalia 'if user.role == "admin":...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if user.role == "admin":
        return True
# Lógica de decisão (if): Avalia 'if not user.permissions:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not user.permissions:
        return False
    perms = [p.strip().lower() for p in user.permissions.split(",")]
    return required_perm.lower() in perms or "*" in perms

def check_permission(required_perm: str, credentials: HTTPAuthorizationCredentials, db: Session) -> str:
    """
    Função/Método check_permission.

    O que faz: Processa check_permission recebendo os parâmetros (required_perm, credentials, db) no contexto de o módulo core/base auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação check_permission seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
# Lógica de decisão (if): Avalia 'if not payload:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not payload:
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado")
    email = payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
# Lógica de decisão (if): Avalia 'if not user:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not user:
        raise HTTPException(status_code=403, detail="Usuário não encontrado.")
# Lógica de decisão (if): Avalia 'if not user_has_permission(use...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not user_has_permission(user, required_perm):
        raise HTTPException(
            status_code=403,
            detail=f"Acesso negado: você não possui a permissão '{required_perm}' necessária."
        )
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
