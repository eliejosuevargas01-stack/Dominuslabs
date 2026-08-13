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


def clean_pem_content(raw_pem: str) -> str:
    """
    Sanitiza strings PEM vindas de variáveis de ambiente:
    Remove aspas externas, substitui \\n por quebras de linha reais e garante final de linha.
    """
    if not raw_pem:
        return ""
    cleaned = raw_pem.strip().strip('"').strip("'").replace("\\n", "\n").strip()
    if not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned


def create_ssl_context(service_name: str = "default") -> ssl.SSLContext | None:
    """
    Cria e retorna o SSLContext configurado com os certificados mTLS do Dominius.
    Suporta variáveis genéricas (MTLS_CERT_CONTENT) ou dedicadas por serviço.
    """
    if not settings.ENABLE_MTLS:
        logger.debug("[mTLS] mTLS está desativado na configuração (ENABLE_MTLS=False)")
        return None

    cert_path = settings.MTLS_CERT_PATH
    key_path = settings.MTLS_KEY_PATH
    ca_path = settings.MTLS_CA_CERT_PATH

    cert_content = ""
    key_content = ""

    if service_name == "identity":
        cert_content = clean_pem_content(os.getenv("IDENTITY_MTLS_CERT_CONTENT", ""))
        key_content = clean_pem_content(os.getenv("IDENTITY_MTLS_KEY_CONTENT", ""))
    elif service_name == "whatsapp":
        cert_content = clean_pem_content(os.getenv("WHATSAPP_MTLS_CERT_CONTENT", ""))
        key_content = clean_pem_content(os.getenv("WHATSAPP_MTLS_KEY_CONTENT", ""))

    # Fallback para variáveis genéricas se as dedicadas não existirem
    if not cert_content:
        cert_content = clean_pem_content(os.getenv("MTLS_CERT_CONTENT", ""))
    if not key_content:
        key_content = clean_pem_content(os.getenv("MTLS_KEY_CONTENT", ""))

    # Se o certificado e a chave forem fornecidos via variável de ambiente em memória
    if cert_content and key_content:
        tmp_cert = f"/tmp/dominus_{service_name}_mtls_cert.pem"
        tmp_key = f"/tmp/dominus_{service_name}_mtls_key.pem"
        try:
            with open(tmp_cert, "w", encoding="utf-8") as f_cert:
                f_cert.write(cert_content)
            with open(tmp_key, "w", encoding="utf-8") as f_key:
                f_key.write(key_content)

            cert_path = tmp_cert
            key_path = tmp_key
            logger.info(f"[mTLS] Certificados mTLS para '{service_name}' sanitizados e escritos em {tmp_cert}.")
        except Exception as e:
            logger.error(f"[mTLS] Falha ao escrever certificados temporários para '{service_name}': {e}")

    if not cert_path or not key_path or not os.path.exists(cert_path) or not os.path.exists(key_path):
        logger.warning(
            f"[mTLS] Certificados não encontrados para '{service_name}': cert={cert_path}, key={key_path}. "
            "Operando em modo SSL padrão sem cliente mTLS."
        )
        return None

    try:
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.SERVER_AUTH,
            cafile=ca_path if ca_path and os.path.exists(ca_path) else None,
        )
        ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        logger.info(f"[mTLS] SSLContext carregado com sucesso para '{service_name}' utilizando cert: {cert_path}")
        return ssl_context
    except Exception as e:
        logger.error(f"[mTLS] ⚠️ Falha ao carregar a cadeia de certificados PEM para '{service_name}': {e}. Operando em HTTPS seguro padrão.")
        return None


def get_mtls_async_client(timeout: float = 15.0, service_name: str = "default") -> httpx.AsyncClient:
    """
    Retorna uma instância de httpx.AsyncClient pronta para realizar requisições mTLS para o serviço alvo.
    """
    ssl_context = create_ssl_context(service_name=service_name)
    if ssl_context:
        return httpx.AsyncClient(verify=ssl_context, timeout=timeout)
    else:
        return httpx.AsyncClient(timeout=timeout)
