"""
Documentação do módulo whatsapp.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para whatsapp.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para whatsapp funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Request
from sqlalchemy.orm import Session
import httpx
from typing import Optional, Dict, Any
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user, check_crm_permission
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
import logging
from app.core.http_client import get_async_client

logger = logging.getLogger("whatsapp")
router = APIRouter()

async def get_user_m2m_headers(email: str, db: Session, scope: str = "whatsapp:sessions:read") -> Dict[str, str]:
    """
    Função/Método get_user_m2m_headers.

    O que faz: Recuperação de dados cadastrados para get_user_m2m_headers recebendo os parâmetros (email, db, scope) no contexto de o endpoint de API para whatsapp.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_user_m2m_headers seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    user = await run_in_threadpool(lambda: db.query(User).filter(User.email == email).first())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    from app.services.whatsapp_service import get_oauth_token, get_tenant_id_for_user
    try:
        tenant_id = await get_tenant_id_for_user(user, db)
        token = await get_oauth_token(user, db, scope=scope)
        headers = {
            "x-session-token": token,
            "x-tenant-id": tenant_id,
            "Authorization": f"Bearer {token}"
        }
        if getattr(settings, "WHATSAPP_MASTER_SECRET", None):
            headers["X-Master-API-Key"] = settings.WHATSAPP_MASTER_SECRET
        return headers
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=f"WhatsApp não vinculado. {str(e)}"
        )

async def get_user_token(email: str, db: Session, scope: str = "whatsapp:sessions:read") -> str:
    """
    Função/Método get_user_token.

    O que faz: Recuperação de dados cadastrados para get_user_token recebendo os parâmetros (email, db, scope) no contexto de o endpoint de API para whatsapp.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_user_token seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    headers = await get_user_m2m_headers(email, db, scope=scope)
    return headers.get("x-session-token", "")

async def make_whatsapp_api_request(
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0
) -> Any:
    """
    Função/Método make_whatsapp_api_request.

    O que faz: Processa make_whatsapp_api_request recebendo os parâmetros (method, path, headers, json_data, timeout) no contexto de o endpoint de API para whatsapp.
    Impacto na regra de negócio: Assegura que o fluxo da operação make_whatsapp_api_request seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    clean_path = path if path.startswith("/") else f"/{path}"
    base_url = settings.WHATSAPP_API_URL.rstrip("/")
    if base_url.startswith("http://") and ":3000" in base_url:
        base_url = base_url.replace("http://", "https://", 1)
    
    import urllib.parse, socket, asyncio
    parsed = urllib.parse.urlparse(base_url)
    is_resolvable = False
    if parsed.hostname:
        try:
            await asyncio.get_running_loop().getaddrinfo(parsed.hostname, None)
            is_resolvable = True
        except Exception:
            is_resolvable = False

    if not is_resolvable:
        logger.error(f"[make_whatsapp_api_request] Não foi possível resolver o hostname '{parsed.hostname}'.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível resolver o endereço da API de WhatsApp."
        )

    url = f"{base_url}{clean_path}"

    req_headers = dict(headers) if headers else {}
    tenant_id = req_headers.get("x-tenant-id")
    if not tenant_id:
        logger.error("[make_whatsapp_api_request] Chamada à Whats API sem x-tenant-id explícito. Operação fail-closed.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: x-tenant-id obrigatório para chamadas à Whats API."
        )

    if "x-session-token" in req_headers:
        token = req_headers["x-session-token"]
        if "Authorization" not in req_headers and token:
            req_headers["Authorization"] = f"Bearer {token}"
    if "Authorization" not in req_headers or not req_headers.get("Authorization"):
        try:
            from app.services.identity_service import get_m2m_jwt
            if "messages" in clean_path or "send" in clean_path:
                scope = "whatsapp:messages:send"
            elif method.upper() in ("POST", "PUT", "DELETE", "PATCH"):
                scope = "whatsapp:sessions:write"
            else:
                scope = "whatsapp:sessions:read"
            token = await get_m2m_jwt(tenant_id=tenant_id, scope=scope)
            if token:
                req_headers["x-session-token"] = token
                req_headers["Authorization"] = f"Bearer {token}"
                req_headers["x-tenant-id"] = tenant_id
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"[make_whatsapp_api_request] Não foi possível obter JWT M2M do Identity Provider: {e}")

    # Always include the Master API Key if configured (read from settings, never hardcoded)
    if "X-Master-API-Key" not in req_headers:
        master_secret = getattr(settings, "WHATSAPP_MASTER_SECRET", None)
        if master_secret and master_secret != "default_master_secret":
            req_headers["X-Master-API-Key"] = master_secret

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    async with get_async_client(timeout=timeout, service_name="whatsapp") as client:
        last_exception = None
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.request(
                    method,
                    url,
                    headers=req_headers,
                    json=json_data
                )
                if response.status_code not in (502, 503, 504, 408):
                    break
                else:
                    logger.warning(f"WhatsApp API returned {response.status_code}. Retrying {attempt+1}/{MAX_RETRIES}...")
                    import asyncio
                    await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
            except Exception as e:
                last_exception = e
                logger.warning(f"WhatsApp API request failed: {e}. Retrying {attempt+1}/{MAX_RETRIES}...")
                import asyncio
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
        
        if response is None:
            logger.error(f"[FLOW-STEP 6] ERROR: WhatsApp API request failed ({last_exception})")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Falha de comunicação com WhatsApp API após retentativas: {str(last_exception)}"
            )

        if response.status_code >= 400:
            logger.error(f"[FLOW-STEP 6] WhatsApp API returned error {response.status_code}: {response.text}")
            try:
                error_data = response.json()
            except Exception:
                error_data = {"detail": response.text}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_data.get("detail", error_data.get("message", "WhatsApp API error"))
            )

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        elif "image/" in content_type or "audio/" in content_type or "video/" in content_type or "application/pdf" in content_type or "application/octet-stream" in content_type:
            return {
                "_is_binary": True,
                "content": response.content,
                "content_type": content_type
            }
        else:
            try:
                return response.json()
            except Exception:
                return response.text

from fastapi.responses import RedirectResponse, Response, StreamingResponse

@router.get("/sessions/{session_id}/avatar")
async def get_session_avatar(
    request: Request,
    session_id: str,
    jid: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Proxy de imagem de perfil de contato/grupo via HTTPS/TLS.
    Evita erros de NS_BINDING_ABORTED e SSL em requisições cross-origin do navegador.
    Aceita Authorization: Bearer ou parâmetro de consulta 'token'.
    """
    auth_header = request.headers.get("Authorization", "")
    effective_token = token or (auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None)
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou ausente."
        )

    try:
        from app.core.auth import decode_access_token
        payload = decode_access_token(effective_token) or jwt.decode(effective_token, settings.SECRET_KEY, algorithms=["HS256"])
        sub = payload.get("sub") if payload else None
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticação inválido ou ausente."
            )
        sub_str = str(sub)
        if sub_str.isdigit():
            user = db.query(User).filter((User.email == sub_str) | (User.id == int(sub_str))).first()
        else:
            user = db.query(User).filter(User.email == sub_str).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )
        from app.services.whatsapp_service import resolve_owned_whatsapp_session
        resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
        user_headers = await get_user_m2m_headers(user.email, db)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou ausente."
        )

    try:
        clean_path = f"/api/sessions/{resolved_session}/avatar?jid={jid}&json=true"
        res = await make_whatsapp_api_request(
            "GET",
            clean_path,
            headers=user_headers
        )
        if isinstance(res, dict):
            if res.get("_is_binary") and res.get("content"):
                return Response(
                    content=res["content"],
                    media_type=res.get("content_type") or "image/jpeg",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
            url_target = res.get("url") or res.get("avatar_url") or res.get("profile_pic_url") or res.get("profile_url") or res.get("avatar")
            if url_target and str(url_target).startswith("http"):
                return RedirectResponse(
                    url_target,
                    status_code=302,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
    except Exception as e:
        pass
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar não encontrado.")

@router.get("/sessions/{session_id}/media")
async def get_session_media(
    request: Request,
    session_id: str,
    token: Optional[str] = Query(None),
    messageId: Optional[str] = None,
    message_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Proxy de mídia (imagens, áudios, vídeos e documentos) da WhatsApp API via HTTPS/TLS.
    Retorna o streaming de binário com o Content-Type correto usando StreamingResponse.
    Aceita Authorization: Bearer ou parâmetro de consulta 'token'.
    """
    auth_header = request.headers.get("Authorization", "")
    effective_token = token or (auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None)
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou ausente."
        )

    try:
        from app.core.auth import decode_access_token
        payload = decode_access_token(effective_token) or jwt.decode(effective_token, settings.SECRET_KEY, algorithms=["HS256"])
        sub = payload.get("sub") if payload else None
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticação inválido ou ausente."
            )
        sub_str = str(sub)
        if sub_str.isdigit():
            user = db.query(User).filter((User.email == sub_str) | (User.id == int(sub_str))).first()
        else:
            user = db.query(User).filter(User.email == sub_str).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )
        from app.services.whatsapp_service import resolve_owned_whatsapp_session
        resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
        user_headers = await get_user_m2m_headers(user.email, db)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou ausente."
        )

    target_msg_id = messageId or message_id
    if not target_msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

    base_url = settings.WHATSAPP_API_URL.rstrip("/")
    if base_url.startswith("http://") and ":3000" in base_url:
        base_url = base_url.replace("http://", "https://", 1)

    clean_path = f"/api/sessions/{resolved_session}/media?messageId={target_msg_id}"
    url = f"{base_url}{clean_path}"

    req_headers = dict(user_headers) if user_headers else {}
    if "x-session-token" in req_headers:
        token_val = req_headers["x-session-token"]
        if "Authorization" not in req_headers and token_val:
            req_headers["Authorization"] = f"Bearer {token_val}"

    if "X-Master-API-Key" not in req_headers:
        master_secret = getattr(settings, "WHATSAPP_MASTER_SECRET", None)
        if master_secret and master_secret != "default_master_secret":
            req_headers["X-Master-API-Key"] = master_secret

    client = httpx.AsyncClient(timeout=60.0)
    try:
        req = client.build_request("GET", url, headers=req_headers)
        response = await client.send(req, stream=True)
    except Exception as e:
        await client.aclose()
        logger.error(f"[WA-MEDIA] Erro ao buscar mídia proxy para session={session_id}, msg={target_msg_id}: {e}")
        raise HTTPException(status_code=502, detail="Falha ao conectar à API de WhatsApp.")

    if response.status_code >= 400:
        await response.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=response.status_code,
            detail="Mídia não encontrada ou indisponível."
        )

    content_type = response.headers.get("content-type", "application/octet-stream")

    async def media_stream():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        content=media_stream(),
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400"
        }
    )

@router.get("/sessions")
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    List all sessions (WhatsApp and Instagram) belonging to the authenticated user.
    """
    headers = await get_user_m2m_headers(current_user, db)
    return await make_whatsapp_api_request(
        "GET",
        "/api/sessions",
        headers=headers
    )

@router.post("/sessions")
async def create_session(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Create a new WhatsApp session and persist positive tenant ownership.
    """
    name = payload.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nome da sessão é obrigatório."
        )

    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if not user.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado: usuário não possui tenant_id configurado.")

    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:sessions:write")
    res = await make_whatsapp_api_request(
        "POST",
        "/api/sessions",
        headers=headers,
        json_data={"name": name, "authToken": headers.get("x-session-token")},
        timeout=15.0
    )

    existing_acc = db.query(WhatsappAccount).filter(
        WhatsappAccount.idpw == name,
        WhatsappAccount.tenant_id == user.tenant_id
    ).first()
    if not existing_acc:
        new_acc = WhatsappAccount(
            user_id=user.id,
            tenant_id=user.tenant_id,
            idpw=name
        )
        db.add(new_acc)
        db.commit()

    return res

@router.get("/sessions/{session_id}")
async def get_session_status(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get the details and status of a WhatsApp session with positive ownership verification.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    headers = await get_user_m2m_headers(current_user, db)
    return await make_whatsapp_api_request(
        "GET",
        f"/api/sessions/{resolved_session}",
        headers=headers
    )

@router.post("/sessions/{session_id}/connect")
async def connect_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Request connection (pairing QR Code) for a WhatsApp session with positive ownership verification.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:sessions:write")
    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{resolved_session}/connect",
        headers=headers,
        timeout=20.0
    )

@router.post("/sessions/{session_id}/disconnect")
async def disconnect_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Disconnect a WhatsApp session with positive ownership verification.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:sessions:write")
    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{resolved_session}/disconnect",
        headers=headers,
        timeout=15.0
    )

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Delete a WhatsApp session with positive ownership verification and local cleanup.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:sessions:write")
    res = await make_whatsapp_api_request(
        "DELETE",
        f"/api/sessions/{resolved_session}",
        headers=headers,
        timeout=15.0
    )
    db.query(WhatsappAccount).filter(
        WhatsappAccount.idpw == resolved_session,
        WhatsappAccount.tenant_id == user.tenant_id
    ).delete()
    db.commit()
    return res

@router.get("/sessions/{session_id}/settings")
async def get_session_settings(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get the webhook and other settings of a WhatsApp session with positive ownership verification.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    headers = await get_user_m2m_headers(current_user, db)
    return await make_whatsapp_api_request(
        "GET",
        f"/api/sessions/{resolved_session}/settings",
        headers=headers
    )

@router.put("/sessions/{session_id}/settings")
async def update_session_settings(
    session_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Update the webhook and other settings of a WhatsApp session with positive ownership verification.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:sessions:write")
    return await make_whatsapp_api_request(
        "PUT",
        f"/api/sessions/{resolved_session}/settings",
        headers=headers,
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
    Send a WhatsApp message directly through a specific session with positive ownership verification.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)

    phone = payload.get("phone") or payload.get("number") or payload.get("jid")
    message = payload.get("message") or payload.get("text") or ""
    media = payload.get("media")

    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O campo 'phone', 'number' ou 'jid' é obrigatório."
        )
        
    if not message and not media:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="É obrigatório enviar 'message' ou 'media'."
        )

    # Extrai só os digitos, mas preserva se o JID já vier no formato correto
    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    final_jid = phone if "@" in str(phone) else f"{cleaned_phone}@s.whatsapp.net"
    
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:messages:send")
    
    json_data = {
        "phone": cleaned_phone,
        "number": cleaned_phone,
        "message": message,
        "text": message,
        "jid": final_jid
    }
    
    if media:
        json_data["media"] = media

    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{resolved_session}/messages/send",
        headers=headers,
        json_data=json_data,
        timeout=30.0 # Timeout aumentado por causa do envio de mídia
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
        
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:sessions:write")
    return await make_whatsapp_api_request(
        "POST",
        "/api/instagram/login",
        headers=headers,
        json_data={"username": username, "password": password, "authToken": headers.get("x-session-token")},
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
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:sessions:write")
    return await make_whatsapp_api_request(
        "POST",
        f"/api/instagram/sessions/{username}/logout",
        headers=headers,
        timeout=15.0
    )



