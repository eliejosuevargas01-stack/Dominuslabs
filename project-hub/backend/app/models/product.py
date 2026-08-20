from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Product(Base):
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
