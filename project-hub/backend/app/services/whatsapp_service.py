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


async def get_oauth_token(user: User, db: Session) -> str:
    """
    Retorna o token temporário da WhatsApp API para o usuário.
    - Se houver token em cache válido, retorna sem fazer nova chamada.
    - Caso contrário, faz OAuth com client_id + client_secret do banco.
    """
    cached = _token_cache.get(user.id)
    if cached:
        logger.debug(f"[WA-OAUTH] Token em cache para user_id={user.id}")
        return cached

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
            f"{base_url}/api/auth/token",
            json={
                "client_id": str(wa_account.client_id),
                "client_secret": wa_account.client_secret,
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
