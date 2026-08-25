"""
Documentação do módulo http_client.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base http_client.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base http_client funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
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
        """
        Função/Método __init__.

        O que faz: Processa __init__ recebendo os parâmetros (service_name) no contexto de o módulo core/base http_client.
        Impacto na regra de negócio: Assegura que o fluxo da operação __init__ seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        super().__init__(*args, **kwargs)
        self.service_name = service_name
        # Mapeamento do service_name interno para a chave do app.core.crypto
        self.target_map = {
            "whatsapp": "whats-api",
            "identity": "idpw",
            "n8n": "n8n"
        }

    async def request(self, method: str, url: str, **kwargs):
        """
        Função/Método request.

        O que faz: Processa request recebendo os parâmetros (method, url) no contexto de o módulo core/base http_client.
        Impacto na regra de negócio: Assegura que o fluxo da operação request seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        # Intercepta POST, PUT, PATCH se houver JSON no kwargs
# Lógica de decisão (if): Avalia 'if method.upper() in ["POST", ...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if method.upper() in ["POST", "PUT", "PATCH"]:
# Lógica de decisão (if): Avalia 'if "json" in kwargs and kwargs...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "json" in kwargs and kwargs["json"] is not None:
                target_key = self.target_map.get(self.service_name, "n8n")
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
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
