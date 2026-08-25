import logging
import httpx
from app.core.crypto import encrypt_payload

logger = logging.getLogger("http_client")

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
                    pass

        return await super().request(method, url, **kwargs)

def get_async_client(timeout: float = 15.0, service_name: str = "default") -> httpx.AsyncClient:
    """
    Retorna uma instância de EncryptedAsyncClient para o serviço alvo,
    com criptografia híbrida automática de payload (Zero-Trust).
    """
    return EncryptedAsyncClient(service_name=service_name, timeout=timeout)
