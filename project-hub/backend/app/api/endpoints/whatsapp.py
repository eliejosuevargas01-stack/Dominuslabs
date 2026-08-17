from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
import httpx
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user, check_crm_permission
from app.models.user import User
import logging
from app.core.mtls_client import get_mtls_async_client

logger = logging.getLogger("whatsapp")
router = APIRouter()

async def get_user_token(email: str, db: Session, scope: str = "whatsapp:sessions:read") -> str:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    # Import inside to avoid circular import issues
    from app.services.whatsapp_service import get_oauth_token
    try:
        # Usa o fluxo M2M OAuth com cache para obter o token JWT com os escopos requisitados
        return await get_oauth_token(user, db, scope=scope)
    except HTTPException as he:
        raise he
    except Exception as e:
        # Se não há credenciais M2M vinculadas ainda, retorna 412
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=f"WhatsApp não vinculado. {str(e)}"
        )

async def make_whatsapp_api_request(
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0
) -> Any:
    clean_path = path if path.startswith("/") else f"/{path}"
    base_url = settings.WHATSAPP_API_URL.rstrip("/")
    if base_url.startswith("http://") and ":3000" in base_url:
        base_url = base_url.replace("http://", "https://", 1)
    
    import urllib.parse, socket, asyncio
    parsed = urllib.parse.urlparse(base_url)
    is_resolvable = False
    if parsed.hostname:
        try:
            socket.gethostbyname(parsed.hostname)
            is_resolvable = True
        except Exception:
            is_resolvable = False

    url = f"{base_url}{clean_path}"
    if not is_resolvable:
        import ssl
        ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        async def check_ip(ip: str):
            try:
                async with httpx.AsyncClient(verify=ctx, timeout=0.5) as test_client:
                    res = await test_client.get(f"https://{ip}:3000/api/health")
                    if res.status_code in (200, 401, 403, 404):
                        return ip
            except Exception:
                pass
            return None
        
        ips = await asyncio.gather(*[check_ip(f"10.0.1.{i}") for i in range(2, 50)])
        valid = [ip for ip in ips if ip]
        if valid:
            url = f"https://{valid[0]}:3000{clean_path}"

    req_headers = dict(headers) if headers else {}
    if "x-session-token" in req_headers:
        token = req_headers["x-session-token"]
        if "Authorization" not in req_headers and token:
            req_headers["Authorization"] = f"Bearer {token}"

    async with get_mtls_async_client(timeout=timeout, service_name="whatsapp") as client:
        try:
            response = await client.request(
                method,
                url,
                headers=req_headers,
                json=json_data
            )
        except Exception as e:
            logger.error(f"[FLOW-STEP 6] ERROR autenticado no whats api com jwt: {e}")
            print(f"[FLOW-STEP 6] ERROR autenticado no whats api com jwt: {e}", flush=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar à API de WhatsApp: {str(e)}"
            )

        if response.status_code >= 400:
            logger.error(f"[FLOW-STEP 6] ERROR autenticado no whats api com jwt: status={response.status_code}")
            print(f"[FLOW-STEP 6] ERROR autenticado no whats api com jwt: status={response.status_code}", flush=True)
        else:
            logger.info(f"[FLOW-STEP 6] autenticado no whats api com jwt: status={response.status_code}")
            print(f"[FLOW-STEP 6] autenticado no whats api com jwt: status={response.status_code}", flush=True)
        
        if response.status_code in (301, 302, 303, 307) and response.headers.get("location"):
            return {"url": response.headers.get("location")}

        content_type = response.headers.get("content-type", "").lower()
        
        # Try decoding JSON if content-type is json or by default
        try:
            res_data = response.json()
            if isinstance(res_data, dict) and res_data.get("_encrypted") is True:
                from app.core.crypto import decrypt_payload
                res_data = decrypt_payload(res_data)
            if response.status_code >= 400:
                detail_msg = res_data.get("message") or res_data.get("detail") or "Erro na API de WhatsApp."
                raise HTTPException(status_code=response.status_code, detail=detail_msg)
            return res_data
        except (ValueError, TypeError):
            # If not JSON, but status is 200 OK, return binary data structure
            if response.status_code < 400:
                return {
                    "_is_binary": True,
                    "content": response.content,
                    "content_type": content_type,
                    "status_code": response.status_code,
                    "url": response.headers.get("location") or str(response.url)
                }
            raise HTTPException(
                status_code=response.status_code if response.status_code >= 400 else status.HTTP_502_BAD_GATEWAY,
                detail=f"A API de WhatsApp retornou erro (status {response.status_code}): {response.text[:200]}"
            )

from fastapi.responses import RedirectResponse

@router.get("/sessions/{session_id}/avatar")
async def get_session_avatar(
    session_id: str,
    jid: str,
    db: Session = Depends(get_db)
):
    """
    Proxy de imagem de perfil de contato/grupo via mTLS.
    Evita erros de NS_BINDING_ABORTED e SSL em requisições cross-origin do navegador.
    Acessível por tags <img> do navegador sem exigir token Bearer nos cabeçalhos.
    """
    try:
        clean_path = f"/api/sessions/{session_id}/avatar?jid={jid}&json=true"
        res = await make_whatsapp_api_request(
            "GET",
            clean_path
        )
        if isinstance(res, dict) and res.get("url"):
            return RedirectResponse(
                res["url"],
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=86400"
                }
            )
    except Exception as e:
        pass
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar não encontrado.")

from fastapi.responses import Response

@router.get("/sessions/{session_id}/media")
async def get_session_media(
    session_id: str,
    messageId: Optional[str] = None,
    message_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Proxy de mídia (imagens, áudios, vídeos e documentos) da WhatsApp API via mTLS.
    Retorna o streaming/binário com o Content-Type correto ou redirecionamento.
    Acessível por tags <img>, <video>, <audio> e <a> do navegador sem exigir token Bearer nos cabeçalhos.
    """
    target_msg_id = messageId or message_id
    if not target_msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

    try:
        clean_path = f"/api/sessions/{session_id}/media?messageId={target_msg_id}"
        res = await make_whatsapp_api_request("GET", clean_path, timeout=30.0)

        if isinstance(res, dict):
            if res.get("_is_binary"):
                return Response(
                    content=res["content"],
                    media_type=res.get("content_type") or "application/octet-stream",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
            if res.get("url"):
                return RedirectResponse(
                    res["url"],
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
            if res.get("data") and isinstance(res["data"], str):
                base64_str = res["data"]
                import base64
                if "," in base64_str:
                    header, base64_str = base64_str.split(",", 1)
                    mime_type = header.split(";")[0].replace("data:", "") if "data:" in header else "application/octet-stream"
                else:
                    mime_type = res.get("mimeType") or res.get("mimetype") or "application/octet-stream"
                
                binary_data = base64.b64decode(base64_str)
                return Response(
                    content=binary_data,
                    media_type=mime_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
    except Exception as e:
        print(f"[WA-MEDIA] Erro ao buscar mídia proxy para session={session_id}, msg={target_msg_id}: {e}", flush=True)

    raise HTTPException(status_code=404, detail="Mídia não encontrada ou indisponível.")

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

@router.post("/sessions/{session_id}/messages/send")
async def send_session_message(
    session_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Send a WhatsApp message directly through a specific session.
    """
    phone = payload.get("phone") or payload.get("number")
    message = payload.get("message") or payload.get("text")
    if not phone or not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Os campos 'phone' (ou 'number') e 'message' (ou 'text') são obrigatórios."
        )

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    token = await get_user_token(current_user, db)
    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers={"x-session-token": token},
        json_data={
            "phone": cleaned_phone,
            "number": cleaned_phone,
            "message": message,
            "text": message,
            "jid": f"{cleaned_phone}@s.whatsapp.net"
        },
        timeout=20.0
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

    from app.core.mtls_client import get_mtls_async_client
    from app.services.whatsapp_service import get_tenant_id_for_user

    tenant_id = await get_tenant_id_for_user(user, db)

    try:
        async with get_mtls_async_client(timeout=20.0, service_name="whatsapp") as client:
            print(f"[M2M-AUTH-FLOW] >>> Enviando solicitação mTLS de provisionamento M2M para WhatsApp API: email={user.email}, tenant_id={tenant_id}", flush=True)
            headers = {"X-Master-API-Key": settings.WHATSAPP_MASTER_SECRET} if getattr(settings, "WHATSAPP_MASTER_SECRET", None) else {}
            resp = await client.post(
                provision_url,
                json={"email": user.email, "tenant_id": tenant_id, "password": user.hashed_password},
                headers=headers
            )

            # Caso já exista na WhatsApp API (conflito 409), tenta reprovisionar
            if resp.status_code == 409:
                print(f"[M2M-AUTH-FLOW] >>> Usuário/Tenant já cadastrado na WhatsApp API (409). Tentando REPROVISIONAR...", flush=True)
                reprovision_url = f"{base_url}/api/v1/clients/reprovision"
                resp = await client.post(
                    reprovision_url,
                    json={"email": user.email, "tenant_id": tenant_id, "password": user.hashed_password},
                    headers=headers
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

            # Salva no banco de dados Dominus com vinculação explicita ao tenant_id
            account = db.query(WhatsappAccount).filter(
                WhatsappAccount.user_id == user.id
            ).first()
            if account:
                account.client_id = client_id
                account.client_secret = client_secret
                account.tenant_id = tenant_id
                print(f"[M2M-AUTH-FLOW] >>> Atualizando credenciais M2M existentes com tenant_id={tenant_id}...", flush=True)
            else:
                account = WhatsappAccount(
                    user_id=user.id,
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
                db.add(account)
                print(f"[M2M-AUTH-FLOW] >>> Criando novo registro whatsapp_accounts vinculado ao tenant_id={tenant_id}...", flush=True)

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

