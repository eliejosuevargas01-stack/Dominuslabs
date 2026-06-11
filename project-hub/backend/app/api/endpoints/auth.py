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
    if payload.username != settings.ADMIN_USERNAME or payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos"
        )
    
    access_token = create_access_token(data={"sub": payload.username})
    refresh_token = create_refresh_token(data={"sub": payload.username})
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
    new_access_token = create_access_token(data={"sub": username})
    new_refresh_token = create_refresh_token(data={"sub": username})
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
