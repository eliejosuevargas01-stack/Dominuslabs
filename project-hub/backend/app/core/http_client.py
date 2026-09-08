"""
Documentação do módulo http_client.py.

O que faz: Implementa o transporte HTTP transparente e assíncrono para os serviços internos.
Impacto na regra de negócio: A camada de transporte HTTP é estritamente de transporte (sem mutação
ou re-encriptação de dados). A responsabilidade por assinatura e encriptação Zero-Trust (híbrida
AES-256-GCM + RSA-OAEP) pertence aos clientes de serviço dedicados (IdentityClient, WhatsAppClient, N8NService),
garantindo eliminação total de dupla encriptação e vazamento de payloads.
"""
import httpx

def get_async_client(timeout: float = 15.0) -> httpx.AsyncClient:
    """
    Retorna uma instância assíncrona de httpx.AsyncClient.
    """
    return httpx.AsyncClient(timeout=timeout)
