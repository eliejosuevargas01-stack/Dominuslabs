"""
Documentação do módulo http_client.py.

O que faz: Implementa o transporte HTTP transparente e assíncrono para os serviços internos.
Impacto na regra de negócio: A camada de transporte HTTP é estritamente de transporte (sem mutação
ou re-encriptação de dados). A responsabilidade por assinatura e encriptação Zero-Trust (híbrida
AES-256-GCM + RSA-OAEP) pertence aos clientes de serviço dedicados (IdentityClient, WhatsAppClient, N8NService),
garantindo eliminação total de dupla encriptação e vazamento de payloads.
"""
import logging
import httpx

logger = logging.getLogger("http_client")


class EncryptedAsyncClient(httpx.AsyncClient):
    """
    Subclasse de httpx.AsyncClient mantida para compatibilidade de tipos e rastreabilidade.
    A camada de transporte não realiza mutação automática no corpo das requisições.
    """
    def __init__(self, service_name: str = "default", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name


def get_async_client(timeout: float = 15.0, service_name: str = "default") -> httpx.AsyncClient:
    """
    Retorna uma instância assíncrona de httpx.AsyncClient para o serviço alvo.
    """
    return EncryptedAsyncClient(service_name=service_name, timeout=timeout)
