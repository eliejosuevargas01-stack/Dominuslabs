"""
mTLS HTTP Client Utility
Responsável por criar conexões HTTPS seguras com verificação mTLS (autenticação mTLS de cliente)
para comunicação Dominius ⇄ Identity Worker e Dominius ⇄ WhatsApp API.
"""
import os
import ssl
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("mtls_client")


def create_ssl_context() -> ssl.SSLContext | None:
    """
    Cria e retorna o SSLContext configurado com os certificados mTLS do Dominius.
    Retorna None se mTLS estiver desabilitado ou se os caminhos não existirem.
    """
    if not settings.ENABLE_MTLS:
        logger.debug("[mTLS] mTLS está desativado na configuração (ENABLE_MTLS=False)")
        return None

    cert_path = settings.MTLS_CERT_PATH
    key_path = settings.MTLS_KEY_PATH
    ca_path = settings.MTLS_CA_CERT_PATH

    if not cert_path or not key_path or not os.path.exists(cert_path) or not os.path.exists(key_path):
        logger.warning(
            f"[mTLS] Certificados não encontrados ou inválidos: cert={cert_path}, key={key_path}. "
            "Operando em modo SSL padrão sem cliente mTLS."
        )
        return None

    ssl_context = ssl.create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH,
        cafile=ca_path if ca_path and os.path.exists(ca_path) else None,
    )
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    logger.info(f"[mTLS] SSLContext configurado com sucesso utilizando cert: {cert_path}")
    return ssl_context


def get_mtls_async_client(timeout: float = 15.0) -> httpx.AsyncClient:
    """
    Retorna uma instância de httpx.AsyncClient pronta para realizar requisições mTLS.
    """
    ssl_context = create_ssl_context()
    if ssl_context:
        return httpx.AsyncClient(verify=ssl_context, timeout=timeout)
    else:
        # Se mTLS não estiver ativo localmente, usa verificação TLS padrão ou httpx padrão
        return httpx.AsyncClient(timeout=timeout)
