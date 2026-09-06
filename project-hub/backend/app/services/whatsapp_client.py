"""
WhatsApp Client — Cliente Interno Único para Comunicação com a Whats API

Responsabilidade exclusiva:
- Todo tráfego Dominus ⇄ Whats API passa obrigatoriamente por este cliente.
- Nenhuma rota, controller ou service pode realizar chamadas HTTP diretas à Whats API.
- Obtém JWT M2M legítimo via IdentityClient.
- Cabeçalhos estritos Dominus ⇄ Whats API:
    - Authorization: Bearer <JWT_IDPW>
    - X-Request-ID: <uuid>
    - Idempotency-Key: <uuid>
- Eliminação COMPLETA de:
    - X-Master-API-Key
    - x-session-token
    - x-tenant-id
    - x-user-id
    - authToken
    - token em query string
- Escopos estritos e explícitos por operação (proibida inferência por método HTTP ou caminho).
- Resiliência: timeout explícito e retry seguro com backoff exponencial.
"""
import uuid
import logging
import asyncio
from typing import Optional, Dict, Any, Union
import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.http_client import get_async_client
from app.core.crypto import encrypt_payload, decrypt_payload
from app.services.identity_client import identity_client

logger = logging.getLogger("whatsapp_client")


class WhatsAppClient:
    """
    Cliente único do Dominus para a Whats API.
    """

    def __init__(self, base_url: Optional[str] = None):
        self._base_url_override = base_url

    @property
    def base_url(self) -> str:
        url = (self._base_url_override or settings.WHATSAPP_API_URL).rstrip("/")
        if url.startswith("http://") and ":3000" in url:
            url = url.replace("http://", "https://", 1)
        return url

    async def _execute_request(
        self,
        method: str,
        path: str,
        tenant_id: str,
        scope: str,
        json_data: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
        timeout: float = 15.0
    ) -> Any:
        """
        Executa requisição HTTP à Whats API com headers estritos e M2M JWT do IDPW.
        Headers: ONLY Authorization, X-Request-ID, Idempotency-Key.
        Payload: Hybrid Encryption obrigatória (AES-256-GCM + RSA-OAEP) para operações com body.
        """
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: tenant_id obrigatório para chamadas à Whats API."
            )
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope explícito obrigatório para operação na Whats API."
            )

        # 1. Obter JWT M2M emitido pelo IDPW para este tenant_id e scope
        jwt_token = await identity_client.get_token(
            tenant_id=tenant_id,
            scope=scope,
            aud="whatsapp-api"
        )

        request_id = str(uuid.uuid4())
        clean_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{clean_path}"

        # 2. Montar cabeçalhos estritos (somente Authorization, X-Request-ID, Idempotency-Key)
        req_headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-Request-ID": request_id
        }

        # Idempotency-Key para operações de escrita/mutação
        if idempotency_key:
            req_headers["Idempotency-Key"] = idempotency_key
        elif method.upper() in ("POST", "PUT", "DELETE", "PATCH"):
            req_headers["Idempotency-Key"] = str(uuid.uuid4())

        # Payload com criptografia obrigatória (Zero-Trust fail-closed) para whats-api se houver json_data
        payload_to_send = None
        if json_data is not None:
            try:
                payload_to_send = encrypt_payload(json_data, target="whats-api")
            except Exception as enc_err:
                logger.error(f"[WA-CLIENT] Falha ao criptografar payload para Whats API (fail-closed): {enc_err}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Falha de criptografia obrigatória para Whats API: {enc_err}"
                ) from enc_err

        max_retries = 3
        retry_delay = 1.0
        response = None
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with get_async_client(timeout=timeout, service_name="whatsapp") as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=req_headers,
                        params=query_params,
                        json=payload_to_send
                    )

                # Se status de gateway temporário, retenta com backoff
                if response.status_code in (502, 503, 504, 408) and attempt < max_retries - 1:
                    logger.warning(
                        f"[WA-CLIENT] Whats API retornou {response.status_code} para {clean_path}. "
                        f"Retentando {attempt + 1}/{max_retries}..."
                    )
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                break

            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[WA-CLIENT] Falha de conexão com Whats API ({e}). Retentando {attempt + 1}/{max_retries}..."
                    )
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue

        if response is None:
            logger.error(f"[WA-CLIENT] Falha de comunicação com Whats API após retentativas: {last_exception}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Falha de comunicação com WhatsApp API: {str(last_exception)}"
            )

        # Se credencial rejeitada (401/403), invalida cache para forçar renovação na próxima chamada
        if response.status_code in (401, 403):
            identity_client.invalidate_token(tenant_id=tenant_id, scope=scope, aud="whatsapp-api")
            logger.warning(f"[WA-CLIENT] Whats API rejeitou credencial (status {response.status_code}). Cache M2M invalidado.")
            try:
                err_data = response.json()
                detail_msg = err_data.get("detail") or err_data.get("message") or response.text
            except Exception:
                detail_msg = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=detail_msg or "Acesso negado pela Whats API."
            )

        if response.status_code >= 400:
            logger.error(f"[WA-CLIENT] Whats API retornou erro {response.status_code}: {response.text}")
            try:
                error_data = response.json()
                detail_msg = error_data.get("detail") or error_data.get("message") or response.text
            except Exception:
                detail_msg = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=detail_msg or f"Erro retornado pela Whats API ({response.status_code})"
            )

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            if isinstance(data, dict) and data.get("_encrypted") is True:
                data = decrypt_payload(data)
            return data
        elif any(t in content_type for t in ("image/", "audio/", "video/", "application/pdf", "application/octet-stream")):
            return {
                "_is_binary": True,
                "content": response.content,
                "content_type": content_type
            }
        else:
            try:
                data = response.json()
                if isinstance(data, dict) and data.get("_encrypted") is True:
                    data = decrypt_payload(data)
                return data
            except Exception:
                return response.text

    # =========================================================================
    # Operações Explícitas com Escopos Declarados
    # =========================================================================

    async def list_sessions(self, tenant_id: str) -> Any:
        """
        Lista as sessões autorizadas para o tenant.
        Escopo explícito: whatsapp:sessions:read
        """
        return await self._execute_request(
            method="GET",
            path="/api/sessions",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:read"
        )

    async def get_session_status(self, tenant_id: str, session_id: str) -> Any:
        """
        Obtém status de uma sessão específica.
        Escopo explícito: whatsapp:sessions:read
        """
        return await self._execute_request(
            method="GET",
            path=f"/api/sessions/{session_id}",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:read"
        )

    async def create_session(self, tenant_id: str, session_data: Dict[str, Any]) -> Any:
        """
        Cria uma nova sessão para o tenant.
        Escopo explícito: whatsapp:sessions:create
        """
        return await self._execute_request(
            method="POST",
            path="/api/sessions",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:create",
            json_data=session_data,
            timeout=20.0
        )

    async def connect_session(self, tenant_id: str, session_id: str) -> Any:
        """
        Solicita conexão (QR code) para a sessão.
        Escopo explícito: whatsapp:sessions:write
        """
        return await self._execute_request(
            method="POST",
            path=f"/api/sessions/{session_id}/connect",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:write",
            timeout=20.0
        )

    async def disconnect_session(self, tenant_id: str, session_id: str) -> Any:
        """
        Desconecta uma sessão.
        Escopo explícito: whatsapp:sessions:write
        """
        return await self._execute_request(
            method="POST",
            path=f"/api/sessions/{session_id}/disconnect",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:write",
            timeout=15.0
        )

    async def delete_session(self, tenant_id: str, session_id: str) -> Any:
        """
        Remove uma sessão da Whats API.
        Escopo explícito: whatsapp:sessions:delete
        """
        return await self._execute_request(
            method="DELETE",
            path=f"/api/sessions/{session_id}",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:delete",
            timeout=15.0
        )

    async def get_session_settings(self, tenant_id: str, session_id: str) -> Any:
        """
        Consulta configurações da sessão (webhook, etc.).
        Escopo explícito: whatsapp:sessions:read
        """
        return await self._execute_request(
            method="GET",
            path=f"/api/sessions/{session_id}/settings",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:read"
        )

    async def update_session_settings(self, tenant_id: str, session_id: str, settings_data: Dict[str, Any]) -> Any:
        """
        Atualiza configurações da sessão.
        Escopo explícito: whatsapp:sessions:write
        """
        return await self._execute_request(
            method="PUT",
            path=f"/api/sessions/{session_id}/settings",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:write",
            json_data=settings_data
        )

    async def send_message(
        self,
        tenant_id: str,
        session_id: str,
        message_data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> Any:
        """
        Envia mensagem de texto ou mídia para a Whats API.
        Escopo explícito: whatsapp:messages:send
        """
        return await self._execute_request(
            method="POST",
            path=f"/api/sessions/{session_id}/messages/send",
            tenant_id=tenant_id,
            scope="whatsapp:messages:send",
            json_data=message_data,
            idempotency_key=idempotency_key,
            timeout=35.0
        )

    async def get_session_avatar(self, tenant_id: str, session_id: str, jid: str) -> Any:
        """
        Obtém imagem ou URL de avatar de contato/grupo.
        Escopo explícito: whatsapp:sessions:read
        """
        return await self._execute_request(
            method="GET",
            path=f"/api/sessions/{session_id}/avatar",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:read",
            query_params={"jid": jid, "json": "true"},
            timeout=15.0
        )

    async def get_session_media(self, tenant_id: str, session_id: str, message_id: str) -> httpx.Response:
        """
        Obtém streaming de mídia (áudio, imagem, vídeo, documento).
        Escopo explícito: whatsapp:sessions:read
        Retorna o stream de resposta HTTP diretamente para o proxy de streaming do Dominus.
        """
        jwt_token = await identity_client.get_token(
            tenant_id=tenant_id,
            scope="whatsapp:sessions:read",
            aud="whatsapp-api"
        )

        request_id = str(uuid.uuid4())
        url = f"{self.base_url}/api/sessions/{session_id}/media"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-Request-ID": request_id
        }

        client = httpx.AsyncClient(timeout=60.0)
        try:
            req = client.build_request("GET", url, headers=headers, params={"messageId": message_id})
            response = await client.send(req, stream=True)
        except Exception as e:
            await client.aclose()
            logger.error(f"[WA-CLIENT] Erro ao conectar à Whats API para buscar mídia: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Falha ao conectar à API de WhatsApp."
            )

        if response.status_code >= 400:
            await response.aclose()
            await client.aclose()
            raise HTTPException(
                status_code=response.status_code,
                detail="Mídia não encontrada ou indisponível na Whats API."
            )

        return response

    async def instagram_login(self, tenant_id: str, login_data: Dict[str, Any]) -> Any:
        """
        Autentica sessão Instagram na Whats API.
        Escopo explícito: whatsapp:sessions:write
        """
        return await self._execute_request(
            method="POST",
            path="/api/instagram/login",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:write",
            json_data=login_data,
            timeout=30.0
        )

    async def instagram_logout(self, tenant_id: str, username: str) -> Any:
        """
        Encerra sessão Instagram.
        Escopo explícito: whatsapp:sessions:write
        """
        return await self._execute_request(
            method="POST",
            path=f"/api/instagram/sessions/{username}/logout",
            tenant_id=tenant_id,
            scope="whatsapp:sessions:write",
            timeout=15.0
        )


# Instância singleton do WhatsAppClient
whatsapp_client = WhatsAppClient()
