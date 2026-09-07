"""
WhatsApp API Endpoints — Dominus Controlador de Negócio

Princípios:
1. Autentica usuários finais através de Bearer JWT do Dominus.
2. Resolve o tenant (`tenant_id`) a partir do usuário autenticado.
3. Aplica permissões internas e valida ownership estrito (`user.tenant_id == whatsapp_account.tenant_id`).
   Nenhum fallback: admin, default, null.
4. Toda a comunicação com a Whats API é delegada ao WhatsAppClient interno.
5. O browser nunca conhece credenciais M2M ou o endereço interno da Whats API.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user, check_crm_permission, decode_access_token
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
from app.services.whatsapp_client import whatsapp_client
from app.services.identity_client import identity_client
from app.services.whatsapp_service import resolve_owned_whatsapp_session, get_tenant_id_for_user

logger = logging.getLogger("whatsapp_endpoints")
router = APIRouter()



# =============================================================================
# Rotas Oficiais Dominus
# =============================================================================

@router.get("/sessions")
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Lista sessões autorizadas do tenant.
    Sincroniza contas retornadas na tabela local whatsapp_accounts.
    Elimina qualquer sessão residual 'default'.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    tenant_id = await get_tenant_id_for_user(user, db)
    sessions_data = await whatsapp_client.list_sessions(tenant_id=tenant_id)

    filtered_items = []
    return_data = sessions_data

    if isinstance(sessions_data, list):
        filtered_items = [
            s for s in sessions_data
            if isinstance(s, dict)
            and str(s.get("id") or s.get("sessionId") or "").strip().lower() != "default"
            and str(s.get("name") or "").strip().lower() != "default"
        ]
        return_data = filtered_items
    elif isinstance(sessions_data, dict):
        raw_list = sessions_data.get("sessions") or []
        filtered_items = [
            s for s in raw_list
            if isinstance(s, dict)
            and str(s.get("id") or s.get("sessionId") or "").strip().lower() != "default"
            and str(s.get("name") or "").strip().lower() != "default"
        ]
        return_data = dict(sessions_data)
        return_data["sessions"] = filtered_items

    try:
        # Remove contas legadas 'default' no banco local
        db.query(WhatsappAccount).filter(
            WhatsappAccount.tenant_id == tenant_id,
            WhatsappAccount.session_id.ilike("default")
        ).delete(synchronize_session=False)

        for item in filtered_items:
            if not isinstance(item, dict):
                continue
            candidates = set()
            display_name = item.get("name")
            for key in ("id", "sessionId", "name"):
                val = item.get(key)
                if val and isinstance(val, str) and val.strip():
                    cleaned = val.strip()
                    if cleaned.lower() != "default":
                        candidates.add(cleaned)
                        candidates.add(cleaned.replace(" ", "-"))
                        candidates.add(cleaned.replace("-", " "))

            for cand in candidates:
                existing = db.query(WhatsappAccount).filter(
                    WhatsappAccount.tenant_id == tenant_id,
                    WhatsappAccount.session_id == cand
                ).first()
                if not existing:
                    new_acc = WhatsappAccount(
                        user_id=user.id,
                        tenant_id=tenant_id,
                        session_id=cand,
                        display_name=display_name
                    )
                    db.add(new_acc)
        db.commit()
    except Exception as e:
        logger.warning(f"[WA-SYNC] Falha ao sincronizar sessões com o banco local: {e}")
        db.rollback()

    return return_data


@router.post("/sessions")
async def create_session(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Cria uma nova sessão WhatsApp e vincula ownership positivo com o tenant.
    """
    name = payload.get("name")
    if not name or not str(name).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nome da sessão é obrigatório."
        )
    name = str(name).strip()
    if name.lower() == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nome 'default' é reservado e não pode ser utilizado como sessão."
        )

    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    tenant_id = await get_tenant_id_for_user(user, db)

    # Cria sessão via WhatsAppClient (scope: whatsapp:sessions:create)
    res = await whatsapp_client.create_session(
        tenant_id=tenant_id,
        session_data={"name": name}
    )

    candidates = {
        name,
        name.replace(" ", "-"),
        name.replace("-", " ")
    }
    if isinstance(res, dict):
        for key in ("id", "sessionId", "name"):
            val = res.get(key)
            if val and isinstance(val, str) and val.strip():
                c = val.strip()
                if c.lower() != "default":
                    candidates.add(c)
                    candidates.add(c.replace(" ", "-"))
                    candidates.add(c.replace("-", " "))
        sess_obj = res.get("session")
        if isinstance(sess_obj, dict):
            for key in ("id", "sessionId", "name"):
                val = sess_obj.get(key)
                if val and isinstance(val, str) and val.strip():
                    c = val.strip()
                    if c.lower() != "default":
                        candidates.add(c)
                        candidates.add(c.replace(" ", "-"))
                        candidates.add(c.replace("-", " "))

    for cand in candidates:
        existing_acc = db.query(WhatsappAccount).filter(
            WhatsappAccount.tenant_id == tenant_id,
            WhatsappAccount.session_id == cand
        ).first()
        if not existing_acc:
            new_acc = WhatsappAccount(
                user_id=user.id,
                tenant_id=tenant_id,
                session_id=cand,
                display_name=name
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
    Obtém status da sessão com validação estrita de ownership.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    return await whatsapp_client.get_session_status(
        tenant_id=user.tenant_id,
        session_id=resolved_session
    )


@router.post("/sessions/{session_id}/connect")
async def connect_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Solicita conexão (QR code) com validação estrita de ownership.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    return await whatsapp_client.connect_session(
        tenant_id=user.tenant_id,
        session_id=resolved_session
    )


@router.post("/sessions/{session_id}/disconnect")
async def disconnect_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Desconecta sessão com validação estrita de ownership.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    return await whatsapp_client.disconnect_session(
        tenant_id=user.tenant_id,
        session_id=resolved_session
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Exclui uma sessão WhatsApp com validação estrita de ownership e limpeza no banco local.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    clean_target = (session_id or "").strip()
    if clean_target.lower() == "default":
        # Limpeza limpa e idempotente de registros residuais 'default'
        db.query(WhatsappAccount).filter(
            WhatsappAccount.tenant_id == user.tenant_id,
            WhatsappAccount.session_id.ilike("default")
        ).delete(synchronize_session=False)
        if user.preferred_session_id and user.preferred_session_id.lower() == "default":
            user.preferred_session_id = None
            db.add(user)
        db.commit()
        return {"success": True, "message": "Conexão default removida com sucesso."}

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)

    variants = {
        clean_target,
        clean_target.replace("-", " "),
        clean_target.replace(" ", "-"),
        resolved_session,
        resolved_session.replace("-", " "),
        resolved_session.replace(" ", "-")
    }

    res = None
    try:
        res = await whatsapp_client.delete_session(
            tenant_id=user.tenant_id,
            session_id=resolved_session
        )
    except HTTPException as he:
        if he.status_code == 404:
            logger.info(f"[WA-DELETE] Sessão '{resolved_session}' já não existia na Whats API (404).")
            res = {"success": True, "message": "Sessão removida do servidor."}
        else:
            raise he

    db.query(WhatsappAccount).filter(
        WhatsappAccount.tenant_id == user.tenant_id,
        WhatsappAccount.session_id.in_(variants)
    ).delete(synchronize_session=False)

    if user.preferred_session_id in variants:
        user.preferred_session_id = None
        db.add(user)

    db.commit()
    return res or {"success": True, "message": "Sessão removida com sucesso."}


@router.get("/sessions/{session_id}/settings")
async def get_session_settings(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Consulta configurações da sessão com validação de ownership.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    return await whatsapp_client.get_session_settings(
        tenant_id=user.tenant_id,
        session_id=resolved_session
    )


@router.put("/sessions/{session_id}/settings")
async def update_session_settings(
    session_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Atualiza configurações da sessão com validação de ownership.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    return await whatsapp_client.update_session_settings(
        tenant_id=user.tenant_id,
        session_id=resolved_session,
        settings_data=payload
    )


@router.post("/sessions/{session_id}/messages/send")
async def send_session_message(
    session_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Envia mensagem direta WhatsApp através de uma sessão com validação de ownership.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

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

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    final_jid = phone if "@" in str(phone) else f"{cleaned_phone}@s.whatsapp.net"

    json_data = {
        "phone": cleaned_phone,
        "number": cleaned_phone,
        "message": message,
        "text": message,
        "jid": final_jid
    }
    if media:
        json_data["media"] = media

    return await whatsapp_client.send_message(
        tenant_id=user.tenant_id,
        session_id=resolved_session,
        message_data=json_data
    )


@router.get("/sessions/{session_id}/avatar")
async def get_session_avatar(
    request: Request,
    session_id: str,
    jid: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Proxy de imagem de perfil autenticado pelo Dominus via WhatsAppClient.
    """
    auth_header = request.headers.get("Authorization", "")
    effective_token = token or (auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None)
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou ausente."
        )

    payload = decode_access_token(effective_token)
    sub = payload.get("sub") if payload else None
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    sub_str = str(sub)
    if sub_str.isdigit():
        user = db.query(User).filter((User.email == sub_str) | (User.id == int(sub_str))).first()
    else:
        user = db.query(User).filter(User.email == sub_str).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)

    try:
        res = await whatsapp_client.get_session_avatar(
            tenant_id=user.tenant_id,
            session_id=resolved_session,
            jid=jid
        )
        if isinstance(res, dict):
            if res.get("_is_binary") and res.get("content"):
                return Response(
                    content=res["content"],
                    media_type=res.get("content_type") or "image/jpeg",
                    headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=86400"}
                )
            url_target = res.get("url") or res.get("avatar_url") or res.get("profile_pic_url") or res.get("profile_url") or res.get("avatar")
            if url_target and str(url_target).startswith("http"):
                return RedirectResponse(
                    url_target,
                    status_code=302,
                    headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=86400"}
                )
    except Exception as e:
        logger.warning(f"[WA-AVATAR] Erro ao buscar avatar para jid={jid}: {e}")

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
    Proxy de mídia (áudio, imagem, vídeo) autenticado pelo Dominus via WhatsAppClient.
    """
    auth_header = request.headers.get("Authorization", "")
    effective_token = token or (auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None)
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou ausente."
        )

    payload = decode_access_token(effective_token)
    sub = payload.get("sub") if payload else None
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    sub_str = str(sub)
    if sub_str.isdigit():
        user = db.query(User).filter((User.email == sub_str) | (User.id == int(sub_str))).first()
    else:
        user = db.query(User).filter(User.email == sub_str).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    resolved_session = resolve_owned_whatsapp_session(user, session_id, db)
    target_msg_id = messageId or message_id
    if not target_msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

    response = await whatsapp_client.get_session_media(
        tenant_id=user.tenant_id,
        session_id=resolved_session,
        message_id=target_msg_id
    )

    content_type = response.headers.get("content-type", "application/octet-stream")

    async def media_stream():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()

    return StreamingResponse(
        content=media_stream(),
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400"
        }
    )


# =============================================================================
# Instagram Proxy
# =============================================================================

@router.post("/instagram/login")
async def login_instagram_proxy(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """Autentica conta Instagram."""
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário e senha do Instagram são obrigatórios."
        )

    tenant_id = await get_tenant_id_for_user(user, db)
    return await whatsapp_client.instagram_login(
        tenant_id=tenant_id,
        login_data={"username": username, "password": password}
    )


@router.post("/instagram/sessions/{username}/logout")
async def logout_instagram_proxy(
    username: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """Encerra sessão Instagram."""
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    tenant_id = await get_tenant_id_for_user(user, db)
    return await whatsapp_client.instagram_logout(tenant_id=tenant_id, username=username)
