"""Persistent orders that have been explicitly handed off to the Order Manager."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OrderManagerOrder(Base):
    __tablename__ = "order_manager_orders"
    __table_args__ = (UniqueConstraint("tenant_id", "pedido_id", name="uq_order_manager_tenant_pedido"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    pedido_id = Column(String(255), nullable=False, index=True)
    cliente_id = Column(String(255), nullable=False)
    content_jid = Column(String(255), nullable=False)
    address = Column(String, nullable=False, default="")
    total = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(32), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    accepted_at = Column(DateTime, nullable=True)

    items = relationship("OrderManagerOrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderManagerOrderItem(Base):
    __tablename__ = "order_manager_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_manager_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String(255), nullable=False)
    nome = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    order = relationship("OrderManagerOrder", back_populates="items")
