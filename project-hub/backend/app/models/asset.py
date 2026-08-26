"""
Documentação do módulo asset.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados asset.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados asset funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base

class ProjectAsset(Base):
    """
    Classe ProjectAsset.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectAsset em o modelo de banco de dados asset.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectAsset, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "project_assets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    file_name = Column(String)
    file_type = Column(String)  # image, video, audio, document
    file_path = Column(String)
    file_size = Column(Integer)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    project = relationship("Project", back_populates="assets")