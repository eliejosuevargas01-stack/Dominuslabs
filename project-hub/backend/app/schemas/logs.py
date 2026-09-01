"""
Documentação do módulo logs.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic logs.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic logs funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class CommitLogBase(BaseModel):
    """
    Classe CommitLogBase.

    O que faz: Representa a estrutura de dados e operações para a entidade CommitLogBase em o esquema de validação Pydantic logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CommitLogBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    commit_hash: str
    message: str
    author: str
    commit_date: datetime

class CommitLogCreate(CommitLogBase):
    """
    Classe CommitLogCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade CommitLogCreate em o esquema de validação Pydantic logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CommitLogCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    project_id: int

class CommitLog(CommitLogBase):
    """
    Classe CommitLog.

    O que faz: Representa a estrutura de dados e operações para a entidade CommitLog em o esquema de validação Pydantic logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CommitLog, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    project_id: int

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic logs.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True

class DeployLogBase(BaseModel):
    """
    Classe DeployLogBase.

    O que faz: Representa a estrutura de dados e operações para a entidade DeployLogBase em o esquema de validação Pydantic logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade DeployLogBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    provider: str
    status: str
    deploy_url: Optional[HttpUrl] = None
    deploy_date: datetime

class DeployLogCreate(DeployLogBase):
    """
    Classe DeployLogCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade DeployLogCreate em o esquema de validação Pydantic logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade DeployLogCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    project_id: int

class DeployLog(DeployLogBase):
    """
    Classe DeployLog.

    O que faz: Representa a estrutura de dados e operações para a entidade DeployLog em o esquema de validação Pydantic logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade DeployLog, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    project_id: int

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic logs.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True