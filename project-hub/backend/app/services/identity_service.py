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
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.mtls_client import get_mtls_async_client
from app.core.crypto import decrypt_payload

logger = logging.getLogger("identity_service")

# Cache em memória: chave = (tenant_id, scope), valor = jwt_token
# Validade curta por padrão (5 minutos)
_identity_token_cache: TTLCache = TTLCache(maxsize=512, ttl=300)


async def get_m2m_jwt(tenant_id: str, scope: str = "whatsapp:sessions:read") -> str:
    """
    Obtém um JWT M2M estrito para o tenant_id e scope especificados.
    Tenta primeiro o cache local; se não existir, chama o Identity Worker via mTLS.
    Sem fallbacks ou bypasses de segurança em caso de falha.
    """
    cache_key = (tenant_id, scope)
    cached_token = _identity_token_cache.get(cache_key)
    if cached_token:
        logger.debug(f"[IDENTITY-WORKER] Reutilizando JWT M2M do cache para tenant_id={tenant_id}, scope={scope}")
        return cached_token

    base_url = settings.IDENTITY_WORKER_URL.rstrip("/")
    url = f"{base_url}/v1/tokens"

    headers = {
        "Content-Type": "application/json",
        "cf-client-cert-presented": "1",
        "cf-client-cert-subject-dn": "CN=dominus-prod",
        "cf-client-cert-issuer-dn": "CN=dominus-prod"
    }

    payload = {
        "client_id": "dominus-prod",
        "tenant_id": tenant_id,
        "role": "admin",
        "scope": scope,
        "aud": "whatsapp-api",
        "audience": "whatsapp-api"
    }

    logger.info(f"[IDENTITY-WORKER] Requisitando novo JWT M2M via mTLS para tenant_id={tenant_id}, scope={scope}...")
    print(f"[mTLS-AUDIT] 🔐 Conexão mTLS com Identity Worker NECESSÁRIA (autenticação de certificado cliente Cloudflare): URL={url}", flush=True)

    try:
        async with get_mtls_async_client(timeout=10.0, service_name="identity") as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("_encrypted") is True:
                    try:
                        data = decrypt_payload(data)
                        logger.debug("[IDENTITY-WORKER] Payload de resposta Zero-Trust decriptografado com sucesso.")
                    except Exception as decrypt_err:
                        logger.error(f"[IDENTITY-WORKER] Falha ao decriptografar resposta do Worker: {decrypt_err}")
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Falha ao decriptografar credencial emitida pelo Identity Worker."
                        )

                token = data.get("access_token")
                expires_in = data.get("expires_in", 300)

                if not token:
                    logger.error(f"[IDENTITY-WORKER] Resposta incompleta: {data}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Identity Worker retornou credencial incompleta."
                    )

                _identity_token_cache[cache_key] = token
                logger.info(f"[IDENTITY-WORKER] ✅ JWT M2M emitido com sucesso para tenant_id={tenant_id} (exp={expires_in}s)")
                return token
            elif resp.status_code in (401, 403):
                logger.error(f"[IDENTITY-WORKER] ❌ Autenticação/Permissão recusada pelo Identity Worker: status={resp.status_code}, body={resp.text}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Acesso M2M negado pelo Identity Worker (status {resp.status_code}): {resp.text}"
                )
            else:
                logger.error(f"[IDENTITY-WORKER] Falha na emissão do JWT M2M: status={resp.status_code}, body={resp.text[:200]}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Identity Worker recusou a solicitação M2M (status {resp.status_code})."
                )
    except httpx.RequestError as e:
        logger.error(f"[IDENTITY-WORKER] ❌ Erro de conexão com Identity Worker em {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço Identity Worker inacessível ({url}). Verifique a URL e a conexão mTLS."
        )


def invalidate_m2m_token(tenant_id: str, scope: str = "whatsapp:messages:send") -> None:
    """Invalida o token em cache se for necessário renovação forçada."""
    _identity_token_cache.pop((tenant_id, scope), None)
    logger.info(f"[IDENTITY-WORKER] Token M2M invalidado do cache para tenant_id={tenant_id}")
