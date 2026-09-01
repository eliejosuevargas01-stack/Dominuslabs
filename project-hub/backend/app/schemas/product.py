"""
Documentação do módulo product.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic product.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic product funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    """
    Classe ProductBase.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductBase em o esquema de validação Pydantic product.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    name: str
    category: Optional[str] = None
    price: Optional[float] = 0.0
    description: Optional[str] = None
    available: Optional[bool] = True
    image_url: Optional[str] = None
    stock: Optional[int] = 0

class ProductCreate(ProductBase):
    """
    Classe ProductCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductCreate em o esquema de validação Pydantic product.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    pass

class ProductUpdate(BaseModel):
    """
    Classe ProductUpdate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductUpdate em o esquema de validação Pydantic product.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductUpdate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    available: Optional[bool] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None

class ProductResponse(ProductBase):
    """
    Classe ProductResponse.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductResponse em o esquema de validação Pydantic product.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductResponse, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic product.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        orm_mode = True
