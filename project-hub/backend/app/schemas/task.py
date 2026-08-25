"""
Documentação do módulo task.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic task.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic task funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.task import TaskStatus

class ProjectTaskBase(BaseModel):
    """
    Classe ProjectTaskBase.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectTaskBase em o esquema de validação Pydantic task.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectTaskBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    name: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

class ProjectTaskCreate(ProjectTaskBase):
    """
    Classe ProjectTaskCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectTaskCreate em o esquema de validação Pydantic task.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectTaskCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    project_id: int

class ProjectTaskUpdate(BaseModel):
    """
    Classe ProjectTaskUpdate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectTaskUpdate em o esquema de validação Pydantic task.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectTaskUpdate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class ProjectTask(ProjectTaskBase):
    """
    Classe ProjectTask.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectTask em o esquema de validação Pydantic task.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectTask, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    project_id: int
    completed_at: Optional[datetime] = None
    completed_by_github: bool = False

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic task.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True