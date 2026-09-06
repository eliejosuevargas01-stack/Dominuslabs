"""
Identity Client (Dominus ⇄ Identity Worker / IDPW)

Responsabilidade exclusiva:
- Solicitar e gerenciar JWT M2M para comunicação segura Dominus ⇄ Whats API
- Envelope assinado com a chave privada do Dominus (DOMINUS_PRIVATE_KEY)
- Criptografado com a chave pública do IDPW (IDPW_PUBLIC_KEY)
- Manutenção estritamente em memória (cache volátil TTL)
- NUNCA salva tokens M2M em banco de dados (PostgreSQL), entidades ou frontend.
"""
import uuid
import time
import secrets
import base64
import json
import logging
import httpx
from typing import Optional, Dict, Any
from cachetools import TTLCache
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.crypto import encrypt_payload, decrypt_payload, sign_payload
from app.core.http_client import get_async_client

logger = logging.getLogger("identity_client")


class IdentityClient:
    """
    Cliente único e centralizado para obtenção e validação de tokens M2M junto ao IDPW.
    """
    def __init__(self, cache_ttl: int = 300, cache_maxsize: int = 1024):
        # Cache estritamente em memória: chave = (tenant_id, scope, aud), valor = jwt_token
        self._cache: TTLCache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)

    @staticmethod
    def is_token_still_valid(token: str, margin_seconds: int = 30) -> bool:
        """
        Verifica se o token M2M/JWT é válido e tem mais de `margin_seconds` de vida útil restante.
        """
        if not token or "." not in token:
            return False
        try:
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

    async def get_token(
        self,
        tenant_id: str,
        scope: str,
        aud: str = "whatsapp-api"
    ) -> str:
        """
        Obtém um JWT M2M estrito para o tenant_id, scope e audience especificados.
        Apenas parâmetros de autorização legítimos são transmitidos.
        Não envia role=admin, client_id confiável, user_id, whatsapp_token, etc.
        """
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id é obrigatório para solicitação de token M2M."
            )
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope explícito é obrigatório para solicitação de token M2M."
            )

        cache_key = (tenant_id, scope, aud)
        cached_token = self._cache.get(cache_key)
        if cached_token:
            if self.is_token_still_valid(cached_token, margin_seconds=30):
                logger.debug(f"[IDENTITY-CLIENT] Cache hit para tenant_id={tenant_id}, scope={scope}, aud={aud}")
                return cached_token
            else:
                logger.info(f"[IDENTITY-CLIENT] Token expirando (<30s). Renovando para tenant_id={tenant_id}, scope={scope}...")
                self._cache.pop(cache_key, None)

        base_url = settings.IDENTITY_WORKER_URL.rstrip("/")
        url = f"{base_url}/v1/tokens"

        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        nonce = secrets.token_hex(16)
        jti = str(uuid.uuid4())

        # Payload lógico canônico conforme especificação oficial do GOAL 1
        payload: Dict[str, Any] = {
            "aud": aud,
            "tenant_id": tenant_id,
            "scope": scope,
            "request_id": request_id,
            "timestamp": timestamp,
            "nonce": nonce,
            "jti": jti,
        }

        # 5. Assinar a solicitação com a chave privada do Dominus
        signature = sign_payload(payload)

        # 6. Criar envelope assinado
        envelope: Dict[str, Any] = {
            "aud": aud,
            "tenant_id": tenant_id,
            "scope": scope,
            "request_id": request_id,
            "timestamp": timestamp,
            "nonce": nonce,
            "jti": jti,
            "payload": payload,
            "signature": signature,
            "algorithm": "RS256",
        }

        # Criptografar o envelope com a chave pública do IDPW
        encrypted_body = encrypt_payload(envelope, target="idpw")

        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        }

        logger.info(f"[IDENTITY-CLIENT] Solicitando JWT M2M para tenant_id={tenant_id}, scope={scope}, aud={aud} (req_id={request_id})")

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                async with get_async_client(timeout=10.0, service_name="identity") as client:
                    resp = await client.post(url, json=encrypted_body, headers=headers)

                if resp.status_code in (502, 503, 504, 408) and attempt < max_retries - 1:
                    logger.warning(f"[IDENTITY-CLIENT] IDPW retornou {resp.status_code}. Retentando {attempt + 1}/{max_retries}...")
                    import asyncio
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue

                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and data.get("_encrypted") is True:
                        try:
                            data = decrypt_payload(data)
                            logger.info("[IDENTITY-CLIENT] Resposta do IDPW decriptada com sucesso.")
                        except Exception as dec_err:
                            logger.error(f"[IDENTITY-CLIENT] Falha ao decriptar resposta do IDPW: {dec_err}")
                            raise HTTPException(
                                status_code=status.HTTP_502_BAD_GATEWAY,
                                detail="Falha ao decriptografar credencial emitida pelo Identity Worker."
                            )

                    token = data.get("access_token")
                    expires_in = data.get("expires_in", 300)
                    if not token:
                        logger.error("[IDENTITY-CLIENT] Resposta do IDPW sem access_token.")
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Identity Worker retornou credencial incompleta."
                        )

                    # Armazenar estritamente em memória
                    self._cache[cache_key] = token
                    logger.info(f"[IDENTITY-CLIENT] ✅ JWT M2M emitido com sucesso para tenant_id={tenant_id} (exp={expires_in}s)")
                    return token

                elif resp.status_code in (401, 403):
                    logger.error(f"[IDENTITY-CLIENT] Acesso M2M negado pelo IDPW (status {resp.status_code}): {resp.text}")
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Acesso M2M negado pelo Identity Worker (status {resp.status_code}): {resp.text}"
                    )
                else:
                    logger.error(f"[IDENTITY-CLIENT] Erro inesperado do IDPW (status {resp.status_code}): {resp.text}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Identity Worker recusou a solicitação M2M (status {resp.status_code})."
                    )

            except httpx.RequestError as req_err:
                if attempt < max_retries - 1:
                    logger.warning(f"[IDENTITY-CLIENT] Erro de rede ao conectar ao IDPW: {req_err}. Retentando {attempt + 1}/{max_retries}...")
                    import asyncio
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                logger.error(f"[IDENTITY-CLIENT] IDPW inacessível após retentativas: {req_err}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Serviço Identity Worker inacessível ({url}). Verifique conectividade."
                )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível obter credencial M2M junto ao Identity Worker."
        )

    def invalidate_token(
        self,
        tenant_id: str,
        scope: Optional[str] = None,
        aud: str = "whatsapp-api"
    ) -> None:
        """
        Invalida o token em cache da memória volátil.
        """
        if scope:
            self._cache.pop((tenant_id, scope, aud), None)
        else:
            keys_to_remove = [k for k in list(self._cache.keys()) if k[0] == tenant_id]
            for k in keys_to_remove:
                self._cache.pop(k, None)
        logger.info(f"[IDENTITY-CLIENT] Cache invalidado para tenant_id={tenant_id}, scope={scope}")


# Instância singleton do cliente de identidade
identity_client = IdentityClient()
