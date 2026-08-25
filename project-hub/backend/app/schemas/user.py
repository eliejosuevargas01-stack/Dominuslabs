"""
Documentação do módulo user.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic user.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic user funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """
    Classe UserBase.

    O que faz: Representa a estrutura de dados e operações para a entidade UserBase em o esquema de validação Pydantic user.
    Impacto na regra de negócio: Centraliza o comportamento da entidade UserBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    email: str
    role: str = "custom"
    permissions: str = "read"
    tenant_id: Optional[str] = None
    whatsapp_token: Optional[str] = None

class UserCreate(UserBase):
    """
    Classe UserCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade UserCreate em o esquema de validação Pydantic user.
    Impacto na regra de negócio: Centraliza o comportamento da entidade UserCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    password: str

class UserUpdate(BaseModel):
    """
    Classe UserUpdate.

    O que faz: Representa a estrutura de dados e operações para a entidade UserUpdate em o esquema de validação Pydantic user.
    Impacto na regra de negócio: Centraliza o comportamento da entidade UserUpdate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[str] = None

class UserResponse(UserBase):
    """
    Classe UserResponse.

    O que faz: Representa a estrutura de dados e operações para a entidade UserResponse em o esquema de validação Pydantic user.
    Impacto na regra de negócio: Centraliza o comportamento da entidade UserResponse, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    created_at: datetime

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic user.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True
