from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
import httpx
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user, check_crm_permission
from app.models.user import User

router = APIRouter()

def get_user_token(email: str, db: Session) -> str:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    if not user.whatsapp_token:
        import secrets
        user.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"
        db.commit()
        db.refresh(user)
    return user.whatsapp_token

@router.get("/sessions")
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    List all sessions (WhatsApp and Instagram) belonging to the authenticated user.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.WHATSAPP_API_URL}/api/sessions",
                headers={"x-session-token": token}
            )
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.post("/sessions")
async def create_session(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Create a new WhatsApp session.
    """
    name = payload.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nome da sessão é obrigatório."
        )
        
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{settings.WHATSAPP_API_URL}/api/sessions",
                json={"name": name, "authToken": token}
            )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("message", "Erro ao criar sessão.")
                )
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.get("/sessions/{session_id}")
async def get_session_status(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get the details and status of a WhatsApp session.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.WHATSAPP_API_URL}/api/sessions/{session_id}",
                headers={"x-session-token": token}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Sessão não encontrada ou não pertence a você.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Erro ao buscar status da sessão.")
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.post("/sessions/{session_id}/connect")
async def connect_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Request connection (pairing QR Code) for a WhatsApp session.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(
                f"{settings.WHATSAPP_API_URL}/api/sessions/{session_id}/connect",
                headers={"x-session-token": token}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Sessão não encontrada ou não pertence a você.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Erro ao solicitar conexão da sessão.")
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.post("/sessions/{session_id}/disconnect")
async def disconnect_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Disconnect a WhatsApp session.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{settings.WHATSAPP_API_URL}/api/sessions/{session_id}/disconnect",
                headers={"x-session-token": token}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Sessão não encontrada ou não pertence a você.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Erro ao desconectar sessão.")
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Delete a WhatsApp session.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.delete(
                f"{settings.WHATSAPP_API_URL}/api/sessions/{session_id}",
                headers={"x-session-token": token}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Sessão não encontrada ou não pertence a você.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Erro ao excluir sessão.")
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.get("/sessions/{session_id}/settings")
async def get_session_settings(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get the webhook and other settings of a WhatsApp session.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.WHATSAPP_API_URL}/api/sessions/{session_id}/settings",
                headers={"x-session-token": token}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Sessão não encontrada ou não pertence a você.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Erro ao buscar configurações da sessão.")
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.put("/sessions/{session_id}/settings")
async def update_session_settings(
    session_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Update the webhook and other settings of a WhatsApp session.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.put(
                f"{settings.WHATSAPP_API_URL}/api/sessions/{session_id}/settings",
                headers={"x-session-token": token},
                json=payload
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Sessão não encontrada ou não pertence a você.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Erro ao atualizar configurações da sessão.")
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

# Instagram Proxy Routes
@router.post("/instagram/login")
async def login_instagram_proxy(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Log in to an Instagram account.
    """
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário e senha do Instagram são obrigatórios."
        )
        
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{settings.WHATSAPP_API_URL}/api/instagram/login",
                json={"username": username, "password": password, "authToken": token}
            )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("message", "Falha ao autenticar Instagram.")
                )
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

@router.post("/instagram/sessions/{username}/logout")
async def logout_instagram_proxy(
    username: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Log out of an Instagram account.
    """
    token = get_user_token(current_user, db)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{settings.WHATSAPP_API_URL}/api/instagram/sessions/{username}/logout",
                headers={"x-session-token": token}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Sessão Instagram não encontrada ou não pertence a você.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Erro ao desconectar conta Instagram.")
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )
