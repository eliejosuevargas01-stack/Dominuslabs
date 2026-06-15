from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.core.security import verify_password
from app.core.auth import create_access_token, create_refresh_token, decode_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username
    if "@" not in username:
        username = f"{username}@dominuslabs.online"
        
    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos"
        )
    
    token_data = {
        "sub": user.email,
        "role": user.role,
        "can_create_projects": user.can_create_projects,
        "can_edit_projects": user.can_edit_projects,
        "can_manage_crm": user.can_manage_crm,
        "can_use_scrapper": user.can_use_scrapper
    }
    
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_payload = decode_access_token(payload.refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Token de atualização inválido ou expirado"
        )
    
    email = token_payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado."
        )
        
    token_data = {
        "sub": user.email,
        "role": user.role,
        "can_create_projects": user.can_create_projects,
        "can_edit_projects": user.can_edit_projects,
        "can_manage_crm": user.can_manage_crm,
        "can_use_scrapper": user.can_use_scrapper
    }
    
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
