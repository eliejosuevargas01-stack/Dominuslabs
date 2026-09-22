"""add source_platform and external_order_id to order_manager_orders

Revision ID: 2026092202
Revises: 2026092201
Create Date: 2026-09-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2026092202"
down_revision = "2026092201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_manager_orders",
        sa.Column("source_platform", sa.String(64), nullable=True, index=True),
    )
    op.add_column(
        "order_manager_orders",
        sa.Column("external_order_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_order_manager_orders_source_platform",
        "order_manager_orders",
        ["source_platform"],
    )
    op.create_index(
        "ix_order_manager_orders_external_order_id",
        "order_manager_orders",
        ["external_order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_manager_orders_external_order_id", table_name="order_manager_orders")
    op.drop_index("ix_order_manager_orders_source_platform", table_name="order_manager_orders")
    op.drop_column("order_manager_orders", "external_order_id")
    op.drop_column("order_manager_orders", "source_platform")
