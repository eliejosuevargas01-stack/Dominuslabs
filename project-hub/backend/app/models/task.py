"""
Documentação do módulo task.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados task.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados task funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.core.database import Base

class TaskStatus(str, enum.Enum):
    """
    Classe TaskStatus.

    O que faz: Representa a estrutura de dados e operações para a entidade TaskStatus em o modelo de banco de dados task.
    Impacto na regra de negócio: Centraliza o comportamento da entidade TaskStatus, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class ProjectTask(Base):
    """
    Classe ProjectTask.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectTask em o modelo de banco de dados task.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectTask, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "project_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String)
    description = Column(String, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    completed_at = Column(DateTime, nullable=True)
    completed_by_github = Column(Boolean, default=False)

    project = relationship("Project", back_populates="tasks")