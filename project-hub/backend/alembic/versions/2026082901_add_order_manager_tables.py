"""add persistent Order Manager tables

Revision ID: 2026082901
Revises: 2024082601
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "2026082901"
down_revision = "2024082601"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_manager_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("pedido_id", sa.String(255), nullable=False),
        sa.Column("cliente_id", sa.String(255), nullable=False),
        sa.Column("content_jid", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "pedido_id", name="uq_order_manager_tenant_pedido"),
    )
    op.create_index("ix_order_manager_orders_tenant_id", "order_manager_orders", ["tenant_id"])
    op.create_index("ix_order_manager_orders_pedido_id", "order_manager_orders", ["pedido_id"])
    op.create_index("ix_order_manager_orders_status", "order_manager_orders", ["status"])
    op.create_table(
        "order_manager_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(255), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["order_manager_orders.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_order_manager_order_items_order_id", "order_manager_order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_manager_order_items_order_id", table_name="order_manager_order_items")
    op.drop_table("order_manager_order_items")
    op.drop_index("ix_order_manager_orders_status", table_name="order_manager_orders")
    op.drop_index("ix_order_manager_orders_pedido_id", table_name="order_manager_orders")
    op.drop_index("ix_order_manager_orders_tenant_id", table_name="order_manager_orders")
    op.drop_table("order_manager_orders")
