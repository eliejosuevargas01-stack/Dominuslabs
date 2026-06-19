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

async def make_whatsapp_api_request(
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Any] = None,
    timeout: float = 10.0
) -> Any:
    url = f"{settings.WHATSAPP_API_URL}{path}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json_data
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )
        
        # Verify content-type and try to decode JSON
        try:
            res_data = response.json()
        except (ValueError, TypeError):
            # The response is not JSON (e.g. HTML proxy error)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"A API de WhatsApp retornou uma resposta inválida (status {response.status_code}). É provável que o serviço esteja offline ou instável."
            )
            
        if response.status_code >= 400:
            detail_msg = res_data.get("message") or res_data.get("detail") or "Erro na API de WhatsApp."
            raise HTTPException(
                status_code=response.status_code,
                detail=detail_msg
            )
            
        return res_data

@router.get("/sessions")
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    List all sessions (WhatsApp and Instagram) belonging to the authenticated user.
    """
    token = get_user_token(current_user, db)
    return await make_whatsapp_api_request(
        "GET",
        "/api/sessions",
        headers={"x-session-token": token}
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
    return await make_whatsapp_api_request(
        "POST",
        "/api/sessions",
        json_data={"name": name, "authToken": token},
        timeout=15.0
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
    return await make_whatsapp_api_request(
        "GET",
        f"/api/sessions/{session_id}",
        headers={"x-session-token": token}
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
    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/connect",
        headers={"x-session-token": token},
        timeout=20.0
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
    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/disconnect",
        headers={"x-session-token": token},
        timeout=15.0
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
    return await make_whatsapp_api_request(
        "DELETE",
        f"/api/sessions/{session_id}",
        headers={"x-session-token": token},
        timeout=15.0
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
    return await make_whatsapp_api_request(
        "GET",
        f"/api/sessions/{session_id}/settings",
        headers={"x-session-token": token}
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
    return await make_whatsapp_api_request(
        "PUT",
        f"/api/sessions/{session_id}/settings",
        headers={"x-session-token": token},
        json_data=payload
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
    return await make_whatsapp_api_request(
        "POST",
        "/api/instagram/login",
        json_data={"username": username, "password": password, "authToken": token},
        timeout=30.0
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
    return await make_whatsapp_api_request(
        "POST",
        f"/api/instagram/sessions/{username}/logout",
        headers={"x-session-token": token},
        timeout=15.0
    )

