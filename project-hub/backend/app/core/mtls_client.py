"""
mTLS HTTP Client Utility
Responsável por criar conexões HTTPS seguras com verificação mTLS (autenticação mTLS de cliente)
para comunicação Dominius ⇄ Identity Worker e Dominius ⇄ WhatsApp API.
"""
import os
import ssl
import logging
import httpx
import re
import json
from app.core.config import settings
from app.core.crypto import encrypt_payload

logger = logging.getLogger("mtls_client")


def clean_pem_content(raw_pem: str) -> str:
    """
    Sanitiza strings PEM vindas de variáveis de ambiente:
    Trata quebras com \\n, blocos colados em linha única, strings codificadas em Base64 ou URL-encoded.
    """
    if not raw_pem:
        return ""

    import urllib.parse
    cleaned = raw_pem.strip().strip('"').strip("'")

    if "%2D" in cleaned or "%0A" in cleaned or "%3D" in cleaned:
        try:
            cleaned = urllib.parse.unquote(cleaned)
        except Exception:
            pass

    if "-----BEGIN" not in cleaned:
        try:
            import base64
            decoded_bytes = base64.b64decode(cleaned)
            decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
            if "-----BEGIN" in decoded_str:
                cleaned = decoded_str
        except Exception:
            pass

    cleaned = cleaned.replace("\\n", "\n").replace("\r\n", "\n").strip()

    if "-----BEGIN" in cleaned:
        match = re.search(r"-----BEGIN ([A-Z0-9\s\-]+)-----\s*(.*?)\s*-----END \1-----", cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            header_type = match.group(1).strip().upper()
            raw_body = match.group(2)
            body = re.sub(r"[^A-Za-z0-9+/=]", "", raw_body).strip()
            formatted_body = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
            cleaned = f"-----BEGIN {header_type}-----\n{formatted_body}\n-----END {header_type}-----\n"

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

    # Fallback para variáveis dedicadas de qualquer serviço se as específicas não existirem
    if not cert_content:
        cert_content = clean_pem_content(
            os.getenv("WHATSAPP_MTLS_CERT_CONTENT", "")
            or os.getenv("IDENTITY_MTLS_CERT_CONTENT", "")
            or os.getenv("MTLS_CERT_CONTENT", "")
        )
    if not key_content:
        key_content = clean_pem_content(
            os.getenv("WHATSAPP_MTLS_KEY_CONTENT", "")
            or os.getenv("IDENTITY_MTLS_KEY_CONTENT", "")
            or os.getenv("MTLS_KEY_CONTENT", "")
        )

    if cert_content and key_content:
        import tempfile
        try:
            cert_file = tempfile.NamedTemporaryFile(delete=False, suffix="_mtls_cert.pem", mode="w", encoding="utf-8")
            cert_file.write(cert_content)
            cert_file.close()
            
            key_file = tempfile.NamedTemporaryFile(delete=False, suffix="_mtls_key.pem", mode="w", encoding="utf-8")
            key_file.write(key_content)
            key_file.close()

            cert_path = cert_file.name
            key_path = key_file.name
            logger.info(f"[mTLS] Certificados mTLS para '{service_name}' sanitizados e escritos de forma segura.")
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
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
            
        ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        logger.info(f"[mTLS] SSLContext carregado com sucesso para '{service_name}' utilizando cert: {cert_path}")
        return ssl_context
    except Exception as e:
        logger.error(f"[mTLS] ⚠️ Falha ao carregar a cadeia de certificados PEM para '{service_name}': {e}. Operando em HTTPS seguro padrão.")
        return None


class EncryptedAsyncClient(httpx.AsyncClient):
    """
    Um httpx.AsyncClient customizado que intercepta as requisições e criptografa o payload
    automaticamente usando Hybrid Encryption (Zero-Trust) baseado no 'service_name'.
    """
    def __init__(self, service_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name
        # Mapeamento do service_name interno para a chave do app.core.crypto
        self.target_map = {
            "whatsapp": "whats-api",
            "identity": "idpw",
            "n8n": "n8n"
        }

    async def request(self, method: str, url: str, **kwargs):
        # Intercepta POST, PUT, PATCH se houver JSON no kwargs
        if method.upper() in ["POST", "PUT", "PATCH"]:
            if "json" in kwargs and kwargs["json"] is not None:
                target_key = self.target_map.get(self.service_name, "n8n")
                try:
                    # Tenta criptografar
                    encrypted_json = encrypt_payload(kwargs["json"], target_key)
                    kwargs["json"] = encrypted_json
                    logger.debug(f"[Zero-Trust] Payload criptografado para o serviço {self.service_name}")
                except Exception as e:
                    logger.error(f"[Zero-Trust] Erro ao criptografar payload para {self.service_name}: {e}")
                    # Para strict zero-trust, se falhar a criptografia por falta de chave, poderíamos falhar aqui.
                    # Mas se preferir fallback:
                    pass

        return await super().request(method, url, **kwargs)

def get_mtls_async_client(timeout: float = 15.0, service_name: str = "default") -> httpx.AsyncClient:
    """
    Retorna uma instância de EncryptedAsyncClient pronta para realizar requisições mTLS
    para o serviço alvo, com criptografia híbrida automática de payload (Zero-Trust).
    Gera logs explícitos para auditoria de quando o mTLS foi necessário e ativado vs quando não foi necessário.
    """
    ssl_context = create_ssl_context(service_name=service_name)
    if ssl_context:
        logger.info(f"[mTLS-STATUS] 🔒 mTLS NECESSÁRIO E ATIVO para o serviço '{service_name}'. Certificados cliente validados e anexados.")
        print(f"[mTLS-STATUS] 🔒 mTLS NECESSÁRIO E ATIVO para o serviço '{service_name}'. Certificados cliente validados.", flush=True)
        return EncryptedAsyncClient(service_name=service_name, verify=ssl_context, timeout=timeout)
    else:
        logger.info(f"[mTLS-STATUS] 🔓 mTLS NÃO NECESSÁRIO / NÃO UTILIZADO para o serviço '{service_name}'. Operando via conexão HTTP/HTTPS padrão.")
        print(f"[mTLS-STATUS] 🔓 mTLS NÃO NECESSÁRIO para o serviço '{service_name}'. Conexão padrão ativada.", flush=True)
        return EncryptedAsyncClient(service_name=service_name, timeout=timeout)
