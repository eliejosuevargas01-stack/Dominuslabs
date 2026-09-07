"""
Documentação do módulo product_media.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic product_media.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic product_media funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ProductMediaBase(BaseModel):
    """
    Classe ProductMediaBase.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductMediaBase em o esquema de validação Pydantic product_media.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductMediaBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    product_id: UUID
    media_type: str
    media_url: str

class ProductMediaCreate(ProductMediaBase):
    """
    Classe ProductMediaCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductMediaCreate em o esquema de validação Pydantic product_media.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductMediaCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    tenant_id: Optional[str] = "default"

class ProductMediaResponse(ProductMediaBase):
    """
    Classe ProductMediaResponse.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductMediaResponse em o esquema de validação Pydantic product_media.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductMediaResponse, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    tenant_id: str
    created_at: datetime

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic product_media.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True
