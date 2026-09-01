"""
Documentação do módulo product.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados product.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados product funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime, timezone
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Product(Base):
    """
    Classe Product.

    O que faz: Representa a estrutura de dados e operações para a entidade Product em o modelo de banco de dados product.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Product, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "produtos"

    # Use UUID for postgres compatibility
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, default="default", nullable=False)
    codigo_slug = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    preco = Column(Float, nullable=False, default=0.0)
    disponivel = Column(Boolean, nullable=False, default=True)
    estoque = Column(Integer, nullable=False, default=0)
    imagem_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
