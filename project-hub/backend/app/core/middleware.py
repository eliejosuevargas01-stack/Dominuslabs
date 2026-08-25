"""
Documentação do módulo middleware.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base middleware.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base middleware funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
import time
import json
import base64
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.crypto import decrypt_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enterprise_audit")

def base64url_decode(data: str) -> bytes:
    """
    Função/Método base64url_decode.

    O que faz: Processa base64url_decode recebendo os parâmetros (data) no contexto de o módulo core/base middleware.
    Impacto na regra de negócio: Assegura que o fluxo da operação base64url_decode seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def mask_sensitive_data(data):
    """
    Recursively masks sensitive fields in dictionaries or lists.
    Fields to mask: password, cpf, rg, email, etc.
    """
    sensitive_keys = {"password", "senha", "cpf", "rg", "email", "secret", "token", "credit_card", "cc"}

# Lógica de decisão (if): Avalia 'if isinstance(data, dict):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if isinstance(data, dict):
        masked_data = {}
# Lógica de repetição (for): Itera sobre elementos de 'for k, v in data.ite...' processando múltiplos dados em lote para as regras de domínio.
        for k, v in data.items():
# Lógica de decisão (if): Avalia 'if k.lower() in sensitive_keys...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if k.lower() in sensitive_keys:
                masked_data[k] = "***"
            else:
                masked_data[k] = mask_sensitive_data(v)
        return masked_data
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data

class DecryptionMiddleware(BaseHTTPMiddleware):
    """
    Intercepts incoming requests and decrypts them if they are Hybrid Encrypted.
    """
    async def dispatch(self, request: Request, call_next):
        """
        Função/Método dispatch.

        O que faz: Processa dispatch recebendo os parâmetros (request, call_next) no contexto de o módulo core/base middleware.
        Impacto na regra de negócio: Assegura que o fluxo da operação dispatch seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
# Lógica de decisão (if): Avalia 'if request.method in ["POST", ...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("Content-Type", "")
# Lógica de decisão (if): Avalia 'if "application/json" in conte...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if "application/json" in content_type:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
                try:
                    body = await request.body()
# Lógica de decisão (if): Avalia 'if body:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                    if body:
                        payload = json.loads(body.decode("utf-8"))
                        is_encrypted = False
                        
# Lógica de decisão (if): Avalia 'if isinstance(payload, dict) a...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
                        if isinstance(payload, dict) and str(payload.get("_encrypted", "")).lower() == "true":
                            is_encrypted = True
                        elif isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict) and str(payload[0].get("_encrypted", "")).lower() == "true":
                            is_encrypted = True
                            
# Lógica de decisão (if): Avalia 'if is_encrypted:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                        if is_encrypted:
                            decrypted_payload = decrypt_payload(payload)
                            
                            # Replace the request body with the decrypted one
                            decrypted_bytes = json.dumps(decrypted_payload).encode("utf-8")
                            async def receive_decrypted():
                                """
                                Função/Método receive_decrypted.

                                O que faz: Processa receive_decrypted sem parâmetros específicos no contexto de o módulo core/base middleware.
                                Impacto na regra de negócio: Assegura que o fluxo da operação receive_decrypted seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
                                """
                                return {"type": "http.request", "body": decrypted_bytes}
                            request._receive = receive_decrypted
                            # Also overwrite the cached body so await request.body() returns the decrypted one
                            request._body = decrypted_bytes
                        else:
                            # Restore the original body
                            async def receive_original():
                                """
                                Função/Método receive_original.

                                O que faz: Processa receive_original sem parâmetros específicos no contexto de o módulo core/base middleware.
                                Impacto na regra de negócio: Assegura que o fluxo da operação receive_original seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
                                """
                                return {"type": "http.request", "body": body}
                            request._receive = receive_original
                except Exception as e:
                    logger.error(f"Failed to decrypt incoming request: {e}")
                    return JSONResponse(
                        status_code=400,
                        content={"detail": f"Failed to decrypt the payload. {e}"}
                    )
        
        response = await call_next(request)
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Classe AuditLoggingMiddleware.

    O que faz: Representa a estrutura de dados e operações para a entidade AuditLoggingMiddleware em o módulo core/base middleware.
    Impacto na regra de negócio: Centraliza o comportamento da entidade AuditLoggingMiddleware, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    async def dispatch(self, request: Request, call_next):
        """
        Função/Método dispatch.

        O que faz: Processa dispatch recebendo os parâmetros (request, call_next) no contexto de o módulo core/base middleware.
        Impacto na regra de negócio: Assegura que o fluxo da operação dispatch seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        start_time = time.time()

        # Extract user_id from JWT if present
        user_id = "anonymous"
        auth_header = request.headers.get("Authorization")
# Lógica de decisão (if): Avalia 'if auth_header and auth_header...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
            try:
                parts = token.split('.')
# Lógica de decisão (if): Avalia 'if len(parts) == 3:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
                if len(parts) == 3:
                    payload_b64 = parts[1]
                    payload_json = base64url_decode(payload_b64).decode('utf-8')
                    payload = json.loads(payload_json)
                    user_id = payload.get("sub", payload.get("user_id", "unknown_user"))
            except Exception:
                pass

        # Try to read and mask query params
        query_params = dict(request.query_params)
        masked_query = mask_sensitive_data(query_params) if query_params else {}

        # For masking request body, we must be careful since reading it consumes the stream.
        # But we can just log the path and query for now to avoid consuming the stream and slowing down everything.
        # However, to meet the exact PII masking requirement, we should mask the query string at least,
        # and if the body was already parsed by DecryptionMiddleware, we could log it.
        # But standard audit logs usually just log the metadata + masked query.

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            status_code = response.status_code

            # Formatação de log estruturado exigida para monitoramento e auditoria enterprise
            logger.info(
                f"AUDIT | Timestamp: {time.time()} | ClientIP: {request.client.host if request.client else 'unknown'} "
                f"| UserID: {user_id} | Action: {request.method} {request.url.path} | Query: {json.dumps(masked_query)} "
                f"| Status: {status_code} | Latency: {process_time:.4f}s"
            )

            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"AUDIT ERROR | Timestamp: {time.time()} | ClientIP: {request.client.host if request.client else 'unknown'} "
                f"| UserID: {user_id} | Action: {request.method} {request.url.path} | Query: {json.dumps(masked_query)} "
                f"| Status: 500 | Latency: {process_time:.4f}s | Exception: {str(e)}"
            )
            raise e
