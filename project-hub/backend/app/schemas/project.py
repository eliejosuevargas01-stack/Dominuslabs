"""
Documentação do módulo project.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic project.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic project funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from app.models.project import ProjectStatus

class ProjectBase(BaseModel):
    """
    Classe ProjectBase.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectBase em o esquema de validação Pydantic project.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    name: str
    client_name: str
    description: Optional[str] = None
    project_type: str
    value: float
    status: ProjectStatus = ProjectStatus.NEW
    github_url: Optional[str] = None
    deploy_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    """
    Classe ProjectCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectCreate em o esquema de validação Pydantic project.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    pass

class ProjectUpdate(BaseModel):
    """
    Classe ProjectUpdate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectUpdate em o esquema de validação Pydantic project.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectUpdate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    name: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    value: Optional[float] = None
    status: Optional[ProjectStatus] = None
    github_url: Optional[str] = None
    deploy_url: Optional[str] = None

class ProjectInDBBase(ProjectBase):
    """
    Classe ProjectInDBBase.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectInDBBase em o esquema de validação Pydantic project.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectInDBBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    public_token: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    last_commit_message: Optional[str] = None
    last_deploy_date: Optional[datetime] = None

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic project.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True

class Project(ProjectInDBBase):
    """
    Classe Project.

    O que faz: Representa a estrutura de dados e operações para a entidade Project em o esquema de validação Pydantic project.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Project, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    pass