"""
Documentação do módulo scrape.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic scrape.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic scrape funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class ScrapePayload(BaseModel):
    """
    Classe ScrapePayload.

    O que faz: Representa a estrutura de dados e operações para a entidade ScrapePayload em o esquema de validação Pydantic scrape.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ScrapePayload, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    queries: List[str]
    max_results: Optional[int] = 10
    min_results: Optional[int] = None
    target_platform: Optional[str] = None
    contact_channel: Optional[str] = None
    objective: Optional[str] = None
    webhook_url: Optional[str] = None
