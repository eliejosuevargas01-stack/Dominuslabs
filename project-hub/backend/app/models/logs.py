"""
Documentação do módulo logs.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados logs.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados logs funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class CommitLog(Base):
    """
    Classe CommitLog.

    O que faz: Representa a estrutura de dados e operações para a entidade CommitLog em o modelo de banco de dados logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CommitLog, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "commit_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    commit_hash = Column(String)
    message = Column(String)
    author = Column(String)
    commit_date = Column(DateTime)

    project = relationship("Project", back_populates="commits")

class DeployLog(Base):
    """
    Classe DeployLog.

    O que faz: Representa a estrutura de dados e operações para a entidade DeployLog em o modelo de banco de dados logs.
    Impacto na regra de negócio: Centraliza o comportamento da entidade DeployLog, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "deploy_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    provider = Column(String) # netlify, vercel
    status = Column(String)
    deploy_url = Column(String, nullable=True)
    deploy_date = Column(DateTime)

    project = relationship("Project", back_populates="deploys")