from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.config import settings
from app.core.auth import create_access_token, create_refresh_token, decode_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login")
def login(payload: LoginRequest):
    role = None
    if payload.username == settings.ADMIN_USERNAME and payload.password == settings.ADMIN_PASSWORD:
        role = "admin"
    elif payload.username == settings.VIEWER_USERNAME and payload.password == settings.VIEWER_PASSWORD:
        role = "viewer"
        
    if not role:
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos"
        )
    
    access_token = create_access_token(data={"sub": payload.username, "role": role})
    refresh_token = create_refresh_token(data={"sub": payload.username, "role": role})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh")
def refresh(payload: RefreshRequest):
    token_payload = decode_access_token(payload.refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Token de atualização inválido ou expirado"
        )
    
    username = token_payload.get("sub", "")
    role = token_payload.get("role", "admin")
    new_access_token = create_access_token(data={"sub": username, "role": role})
    new_refresh_token = create_refresh_token(data={"sub": username, "role": role})
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
