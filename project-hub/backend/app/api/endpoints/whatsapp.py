from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
import httpx
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user, check_crm_permission
from app.models.user import User

router = APIRouter()

async def get_user_token(email: str, db: Session) -> str:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    # Import inside to avoid circular import issues
    from app.services.whatsapp_service import get_oauth_token
    try:
        # Usa o fluxo M2M OAuth com cache para obter o token JWT
        return await get_oauth_token(user, db)
    except ValueError as e:
        # Se não há credenciais M2M vinculadas ainda, retorna 412 para o frontend não deslogar
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=f"WhatsApp não vinculado. {str(e)}"
        )

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
    token = await get_user_token(current_user, db)
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
        
    token = await get_user_token(current_user, db)
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
    token = await get_user_token(current_user, db)
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
    token = await get_user_token(current_user, db)
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
    token = await get_user_token(current_user, db)
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
    token = await get_user_token(current_user, db)
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
    token = await get_user_token(current_user, db)
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
    token = await get_user_token(current_user, db)
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
        
    token = await get_user_token(current_user, db)
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
    token = await get_user_token(current_user, db)
    return await make_whatsapp_api_request(
        "POST",
        f"/api/instagram/sessions/{username}/logout",
        headers={"x-session-token": token},
        timeout=15.0
    )


# ---------------------------------------------------------------------------
# Credenciais manuais da WhatsApp API (client_id + client_secret)
# ---------------------------------------------------------------------------

from pydantic import BaseModel
from app.models.whatsapp_account import WhatsappAccount
import uuid as _uuid

class CredentialsPayload(BaseModel):
    client_id: str
    client_secret: str

@router.get("/credentials")
async def get_credentials(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Retorna se o usuário já tem credenciais da WhatsApp API salvas.
    Não expõe o client_secret completo — apenas os primeiros 8 chars.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    account = db.query(WhatsappAccount).filter(
        WhatsappAccount.user_id == user.id
    ).first()

    if not account:
        return {"configured": False, "client_id": None, "client_secret_preview": None}

    return {
        "configured": True,
        "client_id": str(account.client_id),
        "client_secret_preview": account.client_secret[:8] + "••••••••",
        "created_at": account.created_at.isoformat() if account.created_at else None,
    }


@router.put("/credentials")
async def save_credentials(
    payload: CredentialsPayload,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Salva ou atualiza o client_id e client_secret da WhatsApp API para o usuário.
    """
    from app.services.whatsapp_service import invalidate_token

    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Valida UUID
    try:
        client_id_uuid = _uuid.UUID(payload.client_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="client_id inválido — deve ser um UUID.")

    account = db.query(WhatsappAccount).filter(
        WhatsappAccount.user_id == user.id
    ).first()

    print(f"\n[M2M-AUTH-FLOW] >>> Recebendo salvamento MANUAL de credenciais para {user.email}...", flush=True)
    print(f"[M2M-AUTH-FLOW] >>> client_id: {payload.client_id}", flush=True)
    print(f"[M2M-AUTH-FLOW] >>> client_secret: {payload.client_secret[:8]}****************", flush=True)

    if account:
        account.client_id = client_id_uuid
        account.client_secret = payload.client_secret
        print(f"[M2M-AUTH-FLOW] >>> Atualizando registro existente na tabela whatsapp_accounts...", flush=True)
    else:
        account = WhatsappAccount(
            user_id=user.id,
            client_id=client_id_uuid,
            client_secret=payload.client_secret,
        )
        db.add(account)
        print(f"[M2M-AUTH-FLOW] >>> Criando novo registro na tabela whatsapp_accounts...", flush=True)

    db.commit()
    print(f"[M2M-AUTH-FLOW] ✅ Credenciais salvas manualmente no banco de dados Dominus para {user.email}!\n", flush=True)

    # Invalida cache de token OAuth para forçar re-autenticação com as novas credenciais
    invalidate_token(user.id)

    return {
        "ok": True,
        "client_id": str(account.client_id),
        "client_secret_preview": account.client_secret[:8] + "••••••••",
        "message": "Credenciais salvas com sucesso.",
    }


@router.post("/provision")
async def provision_whatsapp(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Vincula o usuário com a WhatsApp API realizando o provisionamento automático.
    Envia o email e a senha criptografada do usuário Dominus e salva o client_id/client_secret.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    base_url = settings.WHATSAPP_API_URL.rstrip("/")
    provision_url = f"{base_url}/api/v1/clients/provision"

    print(f"\n[M2M-AUTH-FLOW] >>> Solicitado VÍNCULO MANUAL para {user.email}", flush=True)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            print(f"[M2M-AUTH-FLOW] >>> Enviando solicitação de provisionamento M2M para a WhatsApp API: email={user.email}", flush=True)
            resp = await client.post(
                provision_url,
                json={"email": user.email, "password": user.hashed_password},
            )

            # Caso já exista na WhatsApp API (conflito 409), podemos tentar obter as chaves?
            # A API WhatsApp não permite obter o client_secret (apenas hash).
            # Mas podemos chamar a rota de /reprovision para resetar o secret e obter o novo!
            if resp.status_code == 409:
                print(f"[M2M-AUTH-FLOW] >>> Usuário já cadastrado na WhatsApp API (409). Tentando REPROVISIONAR para gerar novas credenciais...", flush=True)
                reprovision_url = f"{base_url}/api/v1/clients/reprovision"
                resp = await client.post(
                    reprovision_url,
                    json={"email": user.email, "password": user.hashed_password},
                )

            if resp.status_code not in (200, 201):
                print(f"[M2M-AUTH-FLOW] >>> ❌ Erro ao vincular/reprovisionar na WhatsApp API: status={resp.status_code} body={resp.text[:300]}", flush=True)
                raise HTTPException(
                    status_code=resp.status_code if resp.status_code < 500 else 502,
                    detail=f"Erro na WhatsApp API: {resp.text[:200]}"
                )

            data = resp.json()
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")

            if not client_id or not client_secret:
                print(f"[M2M-AUTH-FLOW] >>> ❌ Resposta inválida da WhatsApp API: {data}", flush=True)
                raise HTTPException(status_code=502, detail="WhatsApp API retornou resposta incompleta.")

            print(f"[M2M-AUTH-FLOW] >>> Cópia de client_id e client_secret recebida com sucesso!", flush=True)
            print(f"[M2M-AUTH-FLOW] >>> client_id: {client_id}", flush=True)
            print(f"[M2M-AUTH-FLOW] >>> client_secret: {client_secret[:8]}****************", flush=True)

            # Salva no banco de dados Dominus
            account = db.query(WhatsappAccount).filter(
                WhatsappAccount.user_id == user.id
            ).first()
            if account:
                account.client_id = client_id
                account.client_secret = client_secret
                print(f"[M2M-AUTH-FLOW] >>> Atualizando credenciais M2M existentes na tabela whatsapp_accounts...", flush=True)
            else:
                account = WhatsappAccount(
                    user_id=user.id,
                    client_id=client_id,
                    client_secret=client_secret
                )
                db.add(account)
                print(f"[M2M-AUTH-FLOW] >>> Criando novo registro na tabela whatsapp_accounts...", flush=True)

            db.commit()
            print(f"[M2M-AUTH-FLOW] ✅ Credenciais M2M vinculadas e salvas no banco com sucesso!\n", flush=True)

            # Invalida cache de token OAuth
            from app.services.whatsapp_service import invalidate_token
            invalidate_token(user.id)

            return {
                "ok": True,
                "client_id": str(client_id),
                "client_secret": client_secret,
                "message": "Vinculado com sucesso!"
            }
    except httpx.HTTPError as e:
        print(f"[M2M-AUTH-FLOW] >>> ❌ Erro de conexão com a WhatsApp API: {str(e)}", flush=True)
        raise HTTPException(status_code=503, detail="Não foi possível conectar à WhatsApp API.")
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[M2M-AUTH-FLOW] >>> ❌ Erro inesperado: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

