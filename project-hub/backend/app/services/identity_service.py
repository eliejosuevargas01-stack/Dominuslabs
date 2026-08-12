"""
Identity Service (Dominius ⇄ mTLS ⇄ Identity Worker)

Responsável por:
1. Conectar ao Identity Worker via mTLS (`dominus-prod`).
2. Solicitar JWT M2M temporário com claims de tenant (`tenant_id`) e escopo da ação (`scope`).
3. Manter cache temporário dos tokens gerados para otimizar chamadas subsequentes.
"""
import logging
import httpx
from cachetools import TTLCache
from app.core.config import settings
from app.core.mtls_client import get_mtls_async_client

logger = logging.getLogger("identity_service")

# Cache em memória: chave = (tenant_id, scope), valor = jwt_token
# Validade curta por padrão (5 minutos)
_identity_token_cache: TTLCache = TTLCache(maxsize=512, ttl=300)


async def get_m2m_jwt(tenant_id: str, scope: str = "whatsapp:messages:send") -> str:
    """
    Obtém um JWT M2M para o tenant_id e scope especificados.
    Tenta primeiro o cache local; se não existir, chama o Identity Worker via mTLS.
    """
    cache_key = (tenant_id, scope)
    cached_token = _identity_token_cache.get(cache_key)
    if cached_token:
        logger.debug(f"[IDENTITY-WORKER] Reutilizando JWT M2M do cache para tenant_id={tenant_id}, scope={scope}")
        return cached_token

    base_url = settings.IDENTITY_WORKER_URL.rstrip("/")
    url = f"{base_url}/api/v1/auth/m2m/token"

    payload = {
        "client_id": "dominus-prod",
        "tenant_id": tenant_id,
        "scope": scope,
        "audience": "whatsapp-api"
    }

    logger.info(f"[IDENTITY-WORKER] Requisitando novo JWT M2M via mTLS para tenant_id={tenant_id}, scope={scope}...")

    try:
        async with get_mtls_async_client(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                expires_in = data.get("expires_in", 300)

                if not token:
                    raise ValueError(f"Identity Worker retornou resposta sem access_token: {data}")

                _identity_token_cache[cache_key] = token
                logger.info(f"[IDENTITY-WORKER] ✅ JWT M2M emitido com sucesso para tenant_id={tenant_id} (exp={expires_in}s)")
                return token
            else:
                logger.error(
                    f"[IDENTITY-WORKER] Falha na emissão do JWT M2M. Status={resp.status_code}, Body={resp.text[:200]}"
                )
                raise ValueError(f"Identity Worker recusou a solicitação mTLS/JWT: status={resp.status_code}")
    except httpx.RequestError as e:
        logger.warning(
            f"[IDENTITY-WORKER] Conexão direta com Identity Worker falhou ({e}). "
            "Operando em fallback de simulação local de token M2M para testes."
        )
        # Fallback de desenvolvimento local se o Worker ainda não estiver publicado no endpoint externo
        import jwt, time
        fallback_token = jwt.encode(
            {
                "iss": "https://identity.dominus.online",
                "aud": "whatsapp-api",
                "sub": "dominus-prod",
                "tenant_id": tenant_id,
                "scope": scope,
                "exp": int(time.time()) + 300,
                "jti": f"fallback_{tenant_id}_{int(time.time())}"
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        _identity_token_cache[cache_key] = fallback_token
        return fallback_token


def invalidate_m2m_token(tenant_id: str, scope: str = "whatsapp:messages:send") -> None:
    """Invalida o token em cache se for necessário renovação forçada."""
    _identity_token_cache.pop((tenant_id, scope), None)
    logger.info(f"[IDENTITY-WORKER] Token M2M invalidado do cache para tenant_id={tenant_id}")
