import secrets
import httpx
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
from app.core.security import verify_password
from app.core.auth import create_access_token, create_refresh_token, decode_access_token

logger = logging.getLogger("whatsapp")
router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# WhatsApp provisioning
# ---------------------------------------------------------------------------

async def _provision_whatsapp_client(user: User, db: Session) -> None:
    """
    Fase 1 do fluxo WhatsApp:
    Chama POST /api/v1/clients/provision na WhatsApp API enviando email+senha
    do usuário Dominus e salva o client_id e client_secret retornados no banco.

    Executada em background após o login — falhas não bloqueiam o login.
    409 da WhatsApp API significa que o usuário já foi provisionado antes;
    nesse caso não fazemos nada (as credenciais já estão no banco).
    """
    base_url = settings.WHATSAPP_API_URL.rstrip("/")
    provision_url = f"{base_url}/api/v1/clients/provision"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            logger.info(f"[WA-PROVISION] Provisionando cliente para {user.email}...")
            resp = await client.post(
                provision_url,
                json={"email": user.email, "password": user.hashed_password},
            )

            if resp.status_code == 409:
                # Já provisionado anteriormente — verifica se temos no banco
                existing = db.query(WhatsappAccount).filter(
                    WhatsappAccount.user_id == user.id
                ).first()
                if existing:
                    logger.info(f"[WA-PROVISION] {user.email} já provisionado (banco OK).")
                else:
                    logger.warning(
                        f"[WA-PROVISION] {user.email} já provisionado na WhatsApp API "
                        f"mas credenciais ausentes no banco Dominus. Reprovisionar manualmente."
                    )
                return

            if resp.status_code not in (200, 201):
                logger.error(
                    f"[WA-PROVISION] ❌ Falha para {user.email}: "
                    f"status={resp.status_code} body={resp.text[:300]}"
                )
                return

            data = resp.json()
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")

            if not client_id or not client_secret:
                logger.error(f"[WA-PROVISION] Resposta inválida da WhatsApp API: {data}")
                return

            # Salva as credenciais no banco Dominus
            wa_account = WhatsappAccount(
                user_id=user.id,
                client_id=str(client_id),
                client_secret=client_secret,
            )
            db.add(wa_account)
            db.commit()
            logger.info(
                f"[WA-PROVISION] ✅ Cliente provisionado para {user.email} "
                f"(client_id={client_id})"
            )

    except Exception as e:
        logger.error(f"[WA-PROVISION] Erro ao provisionar {user.email}: {e}")


async def _maybe_provision(user: User, db: Session) -> None:
    """
    Só chama o provisionamento se o usuário ainda não tiver
    credenciais na tabela whatsapp_accounts.
    """
    existing = db.query(WhatsappAccount).filter(
        WhatsappAccount.user_id == user.id
    ).first()

    if existing:
        logger.debug(f"[WA-PROVISION] {user.email} já tem credenciais — pulando provisão.")
        return

    await _provision_whatsapp_client(user, db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_token_data(user: User) -> dict:
    return {
        "sub": user.email,
        "role": user.role,
        "can_create_projects": user.can_create_projects,
        "can_edit_projects": user.can_edit_projects,
        "can_manage_crm": user.can_manage_crm,
        "can_use_scrapper": user.can_use_scrapper,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(
    payload: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    username = payload.username
    if "@" not in username:
        username = f"{username}@dominuslabs.online"

    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

    # Garante whatsapp_token local (legado — mantido para compatibilidade)
    if not user.whatsapp_token:
        user.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"
        db.commit()
        db.refresh(user)

    # Fase 1: Provisiona cliente na WhatsApp API em background (não bloqueia login)
    background_tasks.add_task(_maybe_provision, user, db)

    token_data = _build_token_data(user)
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "whatsapp_token": user.whatsapp_token,
    }


@router.post("/refresh")
async def refresh(
    payload: RefreshRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    token_payload = decode_access_token(payload.refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de atualização inválido ou expirado")

    email = token_payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    if not user.whatsapp_token:
        user.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"
        db.commit()
        db.refresh(user)

    # Garante provisão em background no refresh também
    background_tasks.add_task(_maybe_provision, user, db)

    token_data = _build_token_data(user)
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "whatsapp_token": user.whatsapp_token,
    }
