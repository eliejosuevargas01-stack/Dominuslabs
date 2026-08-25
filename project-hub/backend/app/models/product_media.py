"""
Documentação do módulo product_media.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados product_media.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados product_media funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base

class ProductMedia(Base):
    """
    Classe ProductMedia.

    O que faz: Representa a estrutura de dados e operações para a entidade ProductMedia em o modelo de banco de dados product_media.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProductMedia, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "product_media"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default", nullable=False)
    product_id = Column(String, index=True, nullable=False)
    media_type = Column(String, nullable=False) # 'image' or 'video'
    media_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
