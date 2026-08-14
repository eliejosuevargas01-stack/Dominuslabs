import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enterprise_audit")

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
