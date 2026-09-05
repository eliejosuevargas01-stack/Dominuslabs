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
from app.core.crypto import decrypt_payload
from app.core.http_client import get_async_client

logger = logging.getLogger("identity_service")

# Cache em memória: chave = (tenant_id, scope), valor = jwt_token
# Validade curta por padrão (5 minutos)
_identity_token_cache: TTLCache = TTLCache(maxsize=512, ttl=300)


async def is_token_still_valid(token: str, margin_seconds: int = 30) -> bool:
    """
    Verifica se o token M2M/JWT é válido e tem mais de `margin_seconds` de vida útil restante.
    """
    if not token or "." not in token:
        return False
    try:
        import base64
        import json
        import time

        parts = token.split(".")
        if len(parts) != 3:
            return False

        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        exp = payload.get("exp", 0)
        return exp > (time.time() + margin_seconds)
    except Exception:
        return False


async def get_m2m_jwt(tenant_id: str, scope: str = "whatsapp:sessions:read") -> str:
    """
    Obtém um JWT M2M estrito para o tenant_id e scope especificados.
    Tenta primeiro o cache local; se não existir ou estiver próximo de expirar (<30s), chama o Identity Worker via mTLS.
    Sem fallbacks ou bypasses de segurança em caso de falha.
    """
    cache_key = (tenant_id, scope)
    cached_token = _identity_token_cache.get(cache_key)
    if cached_token:
        if await is_token_still_valid(cached_token, margin_seconds=30):
            logger.debug(f"[IDENTITY-WORKER] Reutilizando JWT M2M do cache para tenant_id={tenant_id}, scope={scope}")
            return cached_token
        else:
            logger.info(f"[IDENTITY-WORKER] Token em cache próximo do vencimento (<30s). Renovando proativamente para tenant_id={tenant_id}, scope={scope}...")
            _identity_token_cache.pop(cache_key, None)

    base_url = settings.IDENTITY_WORKER_URL.rstrip("/")
    url = f"{base_url}/v1/tokens"

    # Nota de Arquitetura mTLS: A terminação e validação mTLS do Identity Worker ocorre
    # na borda via Cloudflare Access/Tunnel ou pelo contexto TLS gerenciado do cliente HTTP (httpx).
    # Headers simulados cf-client-cert-* foram removidos para evitar fabricação artificial no cliente.
    headers = {
        "Content-Type": "application/json"
    }
    try:
        payload = {
            "client_id": "dominus-prod",
            "tenant_id": tenant_id,
            "role": "admin",
            "scope": scope,
            "aud": "whatsapp-api",
            "audience": "whatsapp-api"
        }
        logger.info("[FLOW-STEP 2] Identity Worker request payload created")
        print("[FLOW-STEP 2] Identity Worker request payload created", flush=True)
    except Exception as create_err:
        logger.error(f"[FLOW-STEP 2] ERROR: Failed to create Identity Worker request payload ({create_err})")
        print(f"[FLOW-STEP 2] ERROR: Failed to create Identity Worker request payload ({create_err})", flush=True)
        raise create_err

    logger.info(f"[IDENTITY-WORKER] Requisitando novo JWT M2M para tenant_id={tenant_id}, scope={scope}...")
    print(f"[AUDIT] 🔐 Conexão com Identity Worker: URL={url}", flush=True)
    try:
        async with get_async_client(timeout=10.0, service_name="identity") as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                logger.info("[FLOW-STEP 4] Received successful response from Identity Worker")
                print("[FLOW-STEP 4] Received successful response from Identity Worker", flush=True)
                data = resp.json()
                if isinstance(data, dict) and data.get("_encrypted") is True:
                    try:
                        data = decrypt_payload(data)
                        logger.info("[FLOW-STEP 5] Identity Worker response payload decrypted successfully")
                        print("[FLOW-STEP 5] Identity Worker response payload decrypted successfully", flush=True)
                    except Exception as decrypt_err:
                        logger.error(f"[FLOW-STEP 5] ERROR: Failed to decrypt Identity Worker response payload ({decrypt_err})")
                        print(f"[FLOW-STEP 5] ERROR: Failed to decrypt Identity Worker response payload ({decrypt_err})", flush=True)
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Falha ao decriptografar credencial emitida pelo Identity Worker."
                        )
                else:
                    logger.info("[FLOW-STEP 5] Identity Worker response payload decrypted successfully")
                    print("[FLOW-STEP 5] Identity Worker response payload decrypted successfully", flush=True)

                token = data.get("access_token")
                expires_in = data.get("expires_in", 300)
                if not token:
                    logger.error("[FLOW-STEP 5] ERROR: Failed to decrypt Identity Worker response payload (access_token missing)")
                    print("[FLOW-STEP 5] ERROR: Failed to decrypt Identity Worker response payload (access_token missing)", flush=True)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Identity Worker retornou credencial incompleta."
                    )

                _identity_token_cache[cache_key] = token
                logger.info(f"[IDENTITY-WORKER] ✅ JWT M2M emitido com sucesso para tenant_id={tenant_id} (exp={expires_in}s)")
                return token
            elif resp.status_code in (401, 403):
                logger.error(f"[FLOW-STEP 4] ERROR: Identity Worker response failed (status {resp.status_code})")
                print(f"[FLOW-STEP 4] ERROR: Identity Worker response failed (status {resp.status_code})", flush=True)
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Acesso M2M negado pelo Identity Worker (status {resp.status_code}): {resp.text}"
                )
            else:
                logger.error(f"[FLOW-STEP 4] ERROR: Identity Worker response failed (status {resp.status_code})")
                print(f"[FLOW-STEP 4] ERROR: Identity Worker response failed (status {resp.status_code})", flush=True)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Identity Worker recusou a solicitação M2M (status {resp.status_code})."
                )
    except httpx.RequestError as e:
        logger.error(f"[FLOW-STEP 4] ERROR: Identity Worker response failed ({e})")
        print(f"[FLOW-STEP 4] ERROR: Identity Worker response failed ({e})", flush=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço Identity Worker inacessível ({url}). Verifique a URL e a conexão mTLS."
        )


def invalidate_m2m_token(tenant_id: str, scope: str = "whatsapp:messages:send") -> None:
    """Invalida o token em cache se for necessário renovação forçada."""
    _identity_token_cache.pop((tenant_id, scope), None)
    logger.info(f"[IDENTITY-WORKER] Token M2M invalidado do cache para tenant_id={tenant_id}")
