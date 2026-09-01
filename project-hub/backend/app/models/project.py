"""
Documentação do módulo project.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados project.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados project funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
import uuid

from app.core.database import Base

class ProjectStatus(str, enum.Enum):
    """
    Classe ProjectStatus.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectStatus em o modelo de banco de dados project.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectStatus, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DEPLOYED = "DEPLOYED"
    DELIVERED = "DELIVERED"

class Project(Base):
    """
    Classe Project.

    O que faz: Representa a estrutura de dados e operações para a entidade Project em o modelo de banco de dados project.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Project, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    public_token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    client_name = Column(String)
    description = Column(String, nullable=True)
    project_type = Column(String)
    value = Column(Float)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.NEW)
    github_url = Column(String, nullable=True)
    deploy_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at = Column(DateTime, nullable=True)
    last_commit_message = Column(String, nullable=True)
    last_deploy_date = Column(DateTime, nullable=True)

    assets = relationship("ProjectAsset", back_populates="project")
    tasks = relationship("ProjectTask", back_populates="project")
    commits = relationship("CommitLog", back_populates="project")
    deploys = relationship("DeployLog", back_populates="project")