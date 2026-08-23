import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.crypto import decrypt_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enterprise_audit")

class DecryptionMiddleware(BaseHTTPMiddleware):
    """
    Intercepts incoming requests and decrypts them if they are Hybrid Encrypted.
    """
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        payload = json.loads(body.decode("utf-8"))
                        is_encrypted = False
                        
                        if isinstance(payload, dict) and str(payload.get("_encrypted", "")).lower() == "true":
                            is_encrypted = True
                        elif isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict) and str(payload[0].get("_encrypted", "")).lower() == "true":
                            is_encrypted = True
                            
                        if is_encrypted:
                            decrypted_payload = decrypt_payload(payload)
                            
                            # Replace the request body with the decrypted one
                            decrypted_bytes = json.dumps(decrypted_payload).encode("utf-8")
                            async def receive_decrypted():
                                return {"type": "http.request", "body": decrypted_bytes}
                            request._receive = receive_decrypted
                            # Also overwrite the cached body so await request.body() returns the decrypted one
                            request._body = decrypted_bytes
                        else:
                            # Restore the original body
                            async def receive_original():
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
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Formatação de log estruturado exigida para monitoramento e auditoria enterprise
            logger.info(
                f"AUDIT | ClientIP: {request.client.host if request.client else 'unknown'} "
                f"| Method: {request.method} | Path: {request.url.path} "
                f"| Status: {response.status_code} | Latency: {process_time:.4f}s"
            )

            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"AUDIT ERROR | ClientIP: {request.client.host if request.client else 'unknown'} "
                f"| Method: {request.method} | Path: {request.url.path} "
                f"| Latency: {process_time:.4f}s | Exception: {str(e)}"
            )
            raise e
