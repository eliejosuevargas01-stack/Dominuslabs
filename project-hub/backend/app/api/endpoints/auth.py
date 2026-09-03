"""
Módulo principal de Autenticação.
Controla o fluxo de login dos usuários corporativos via token JWT local e também engatilha provisionamentos invisíveis na infraestrutura do provedor oficial de WhatsApp, integrando a segurança M2M do ecossistema.
"""
import secrets
import httpx
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.database import get_db, SessionLocal
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
from app.core.security import verify_password
from app.core.auth import create_access_token, create_refresh_token, decode_access_token

logger = logging.getLogger("whatsapp")
router = APIRouter()


class LoginRequest(BaseModel):
    """
    Classe LoginRequest.

    O que faz: Representa a estrutura de dados e operações para a entidade LoginRequest em o endpoint de API para auth.
    Impacto na regra de negócio: Centraliza o comportamento da entidade LoginRequest, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    username: str
    password: str


class RefreshRequest(BaseModel):
    """
    Classe RefreshRequest.

    O que faz: Representa a estrutura de dados e operações para a entidade RefreshRequest em o endpoint de API para auth.
    Impacto na regra de negócio: Centraliza o comportamento da entidade RefreshRequest, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
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
            print(f"\n[M2M-AUTH-FLOW] >>> Enviando solicitação de provisionamento M2M para a WhatsApp API: email={user.email}", flush=True)
            headers = {"X-Master-API-Key": settings.WHATSAPP_MASTER_SECRET} if getattr(settings, "WHATSAPP_MASTER_SECRET", None) else {}
            resp = await client.post(
                provision_url,
                json={"email": user.email, "password": user.hashed_password},
                headers=headers
            )
            if resp.status_code == 409:
                # Já provisionado anteriormente — verifica se temos no banco
                existing = db.query(WhatsappAccount).filter(
                    WhatsappAccount.user_id == user.id
                ).first()
                if existing:
                    logger.info(f"[WA-PROVISION] {user.email} já provisionado (banco OK).")
                    print(f"[M2M-AUTH-FLOW] >>> Usuário {user.email} já possui credenciais provisionadas e salvas no banco.", flush=True)
                else:
                    logger.warning(
                        f"[WA-PROVISION] {user.email} já provisionado na WhatsApp API "
                        f"mas credenciais ausentes no banco Dominus. Reprovisionar manualmente."
                    )
                    print(f"[M2M-AUTH-FLOW] >>> ⚠️ Usuário {user.email} já provisionado na WhatsApp API, mas ausente no banco Dominus. Use a interface para reprovisionar.", flush=True)
                return
            if resp.status_code not in (200, 201):
                logger.error(
                    f"[WA-PROVISION] ❌ Falha para {user.email}: "
                    f"status={resp.status_code} body={resp.text[:300]}"
                )
                print(f"[M2M-AUTH-FLOW] >>> ❌ Erro no provisionamento na WhatsApp API: status={resp.status_code}", flush=True)
                return

            data = resp.json()
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")
            if not client_id or not client_secret:
                logger.error(f"[WA-PROVISION] Resposta inválida da WhatsApp API: {data}")
                print(f"[M2M-AUTH-FLOW] >>> ❌ Resposta inválida da WhatsApp API (faltando client_id ou client_secret): {data}", flush=True)
                return

            print(f"[M2M-AUTH-FLOW] >>> Cópia de client_id e client_secret recebida com sucesso da WhatsApp API!", flush=True)
            print(f"[M2M-AUTH-FLOW] >>> client_id: {client_id}", flush=True)
            print(f"[M2M-AUTH-FLOW] >>> client_secret: {client_secret[:8]}****************", flush=True)
            print(f"[M2M-AUTH-FLOW] >>> Salvando novas credenciais na tabela whatsapp_accounts...", flush=True)

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
            print(f"[M2M-AUTH-FLOW] ✅ Credenciais M2M salvas no banco de dados Dominus com sucesso para {user.email}!\n", flush=True)

    except Exception as e:
        logger.error(f"[WA-PROVISION] Erro ao provisionar {user.email}: {e}")
        print(f"[M2M-AUTH-FLOW] >>> ❌ Erro excepcional ao provisionar {user.email}: {e}", flush=True)


async def _maybe_provision(user_id: int) -> None:
    """
    Só chama o provisionamento se o usuário ainda não tiver
    credenciais na tabela whatsapp_accounts. Instancia sua própria sessão
    do SQLAlchemy e recarrega o usuário pelo ID para evitar DetachedInstanceError.
    """
    db = SessionLocal()
    try:
        existing = db.query(WhatsappAccount).filter(
            WhatsappAccount.user_id == user_id
        ).first()
        if existing:
            logger.debug(f"[WA-PROVISION] Usuário ID {user_id} já tem credenciais — pulando provisão.")
            return

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"[WA-PROVISION] Usuário ID {user_id} não encontrado para provisionamento.")
            return

        await _provision_whatsapp_client(user, db)
    except Exception as e:
        logger.error(f"[WA-PROVISION] Erro inesperado ao tentar provisionar no background para user_id={user_id}: {e}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_token_data(user: User) -> dict:
    """
    Função/Método _build_token_data.

    O que faz: Processa _build_token_data recebendo os parâmetros (user) no contexto de o endpoint de API para auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação _build_token_data seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    role = getattr(user, "role", "custom") or "custom"
    perms = getattr(user, "permissions", "") or "read,write,update,delete"
    is_admin = role == "admin"
    return {
        "sub": user.email,
        "role": role,
        "can_create_projects": getattr(user, "can_create_projects", None) if getattr(user, "can_create_projects", None) is not None else (is_admin or "write" in perms),
        "can_edit_projects": getattr(user, "can_edit_projects", None) if getattr(user, "can_edit_projects", None) is not None else (is_admin or "write" in perms),
        "can_manage_crm": getattr(user, "can_manage_crm", None) if getattr(user, "can_manage_crm", None) is not None else True,
        "can_use_scrapper": getattr(user, "can_use_scrapper", None) if getattr(user, "can_use_scrapper", None) is not None else True,
        "tenant_id": user.tenant_id or "default",
    }


from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Função/Método login.

    O que faz: Processa login recebendo os parâmetros (request, payload, background_tasks, db) no contexto de o endpoint de API para auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação login seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    username = payload.username
    if "@" not in username:
        username = f"{username}@dominuslabs.online"
    if username.lower() in ("eliejousuevargas01@gmail.com", "eliejousuevargas01@dominuslabs.online"):
        username = "Eliejosuevargas01@gmail.com"

    user = db.query(User).filter(User.email == username).first()
# Regra de Segurança Crítica: Bloqueia o acesso (401) instantaneamente caso a senha seja inválida. O timing constante do verify_password evita ataques side-channel e protege os dados do CRM.
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.error("[FLOW-STEP 1] ERROR: User login failed")
        print("[FLOW-STEP 1] ERROR: User login failed", flush=True)
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

    logger.info("[FLOW-STEP 1] User logged in successfully")
    print("[FLOW-STEP 1] User logged in successfully", flush=True)

    # Garante whatsapp_token local
    if not user.whatsapp_token:
        user.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"

    # Fase 1: Provisiona cliente na WhatsApp API em background usando o ID primitivo
    background_tasks.add_task(_maybe_provision, user.id)

    token_data = _build_token_data(user)
    access_token = create_access_token(data=token_data, expires_in=3600)
    refresh_token = create_refresh_token(data=token_data, expires_in=604800)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.access_token = access_token
    user.refresh_token = refresh_token
    user.token_issued_at = now
    user.token_expires_at = now + timedelta(seconds=3600)
    db.commit()
    db.refresh(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "reauth_at_seconds": 3599,
        "whatsapp_token": user.whatsapp_token,
    }


@router.post("/refresh")
def refresh(
    payload: RefreshRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Função/Método refresh.

    O que faz: Processa refresh recebendo os parâmetros (payload, background_tasks, db) no contexto de o endpoint de API para auth.
    Impacto na regra de negócio: Assegura que o fluxo da operação refresh seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    token_payload = decode_access_token(payload.refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de atualização inválido ou expirado")

    email = token_payload.get("sub", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    if not user.whatsapp_token:
        user.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"

    # Garante provisão em background no refresh usando o ID primitivo
    background_tasks.add_task(_maybe_provision, user.id)

    token_data = _build_token_data(user)
    new_access_token = create_access_token(data=token_data, expires_in=3600)
    new_refresh_token = create_refresh_token(data=token_data, expires_in=604800)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.access_token = new_access_token
    user.refresh_token = new_refresh_token
    user.token_issued_at = now
    user.token_expires_at = now + timedelta(seconds=3600)
    db.commit()
    db.refresh(user)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "reauth_at_seconds": 3599,
        "whatsapp_token": user.whatsapp_token,
    }
