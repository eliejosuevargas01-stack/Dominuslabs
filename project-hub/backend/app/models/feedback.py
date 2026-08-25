"""
Documentação do módulo feedback.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados feedback.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados feedback funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class Feedback(Base):
    """
    Classe Feedback.

    O que faz: Representa a estrutura de dados e operações para a entidade Feedback em o modelo de banco de dados feedback.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Feedback, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True)
    final_result = Column(String)
    service_rating = Column(String)
    invested_value_rating = Column(String)
    process_rating = Column(String)
    improvements = Column(String)
    rating = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
