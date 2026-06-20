"""
WhatsApp Service — OAuth + TTLCache
Fase 2 do fluxo: usa client_id/client_secret para obter token temporário.
O token é cacheado por user_id para evitar OAuth a cada mensagem.
"""
import logging
import httpx
from cachetools import TTLCache
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount

logger = logging.getLogger("whatsapp")

# Cache: chave=user_id, valor=access_token
# TTL dinâmico não é suportado pelo TTLCache, então usamos 10 min como padrão seguro.
# O token será renovado automaticamente ao expirar.
_token_cache: TTLCache = TTLCache(maxsize=256, ttl=600)  # 10 min


async def check_token_validity(token: str) -> bool:
    """
    Verifica se o token M2M é válido chamando a WhatsApp API.
    Retorna True se for válido (status 2xx ou 404), False caso contrário.
    """
    if not token:
        return False
    base_url = settings.WHATSAPP_API_URL.rstrip("/")
    url = f"{base_url}/api/sessions"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers={"x-session-token": token})
            # Se retornar 200, 201, 204 ou até 404 (usuário sem credenciais mas token decodificado com sucesso)
            # O importante é não retornar 401 Unauthorized ou 403 Forbidden.
            if resp.status_code in (200, 201, 204, 404):
                logger.info("[WA-OAUTH] Validação do token de sessão: VÁLIDO")
                return True
            logger.warning(f"[WA-OAUTH] Validação do token de sessão falhou com status {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"[WA-OAUTH] Falha de conexão ao verificar token: {e}")
        return False


async def get_oauth_token(user: User, db: Session) -> str:
    """
    Retorna o token temporário da WhatsApp API para o usuário.
    - Se houver token em cache válido, retorna sem fazer nova chamada.
    - Caso contrário, faz OAuth com client_id + client_secret do banco.
    """
    cached = _token_cache.get(user.id)
    if cached:
        logger.debug(f"[WA-OAUTH] Verificando token em cache para user_id={user.id}...")
        if await check_token_validity(cached):
            logger.debug(f"[WA-OAUTH] Token em cache é válido para user_id={user.id}")
            return cached
        else:
            logger.warning(f"[WA-OAUTH] Token em cache é inválido/expirou para user_id={user.id}. Forçando renovação.")
            invalidate_token(user.id)


    # Busca credenciais no banco
    wa_account = db.query(WhatsappAccount).filter(
        WhatsappAccount.user_id == user.id
    ).first()

    if not wa_account:
        raise ValueError(
            f"Usuário {user.email} não tem credenciais WhatsApp. "
            "Faça logout e login novamente para provisionar."
        )

    base_url = settings.WHATSAPP_API_URL.rstrip("/")

    async with httpx.AsyncClient(timeout=15.0) as client:
        logger.info(f"[WA-OAUTH] Obtendo token para user_id={user.id}...")
        resp = await client.post(
            f"{base_url}/api/auth/login",
            json={
                "username": str(wa_account.client_id),
                "password": wa_account.client_secret,
            },
        )

        if resp.status_code != 200:
            raise ValueError(
                f"Falha no OAuth WhatsApp: status={resp.status_code} body={resp.text[:200]}"
            )

        data = resp.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 660)  # segundos; padrão 11 min

        if not access_token:
            raise ValueError(f"OAuth retornou resposta inválida: {data}")

        # Cacheia com TTL = expires_in - 30s (margem de segurança)
        ttl = max(int(expires_in) - 30, 60)
        _token_cache.__setitem__(user.id, access_token)
        # Ajusta TTL dinamicamente recriando a entrada não é possível no TTLCache padrão,
        # então usamos o TTL fixo de 10 min (seguro pois o cache é por user_id).
        logger.info(
            f"[WA-OAUTH] ✅ Token obtido para user_id={user.id} "
            f"(expires_in={expires_in}s, cache_ttl={ttl}s)"
        )
        return access_token


def invalidate_token(user_id: int) -> None:
    """Remove o token do cache forçando novo OAuth na próxima chamada."""
    _token_cache.pop(user_id, None)
    logger.info(f"[WA-OAUTH] Token invalidado para user_id={user_id}")
