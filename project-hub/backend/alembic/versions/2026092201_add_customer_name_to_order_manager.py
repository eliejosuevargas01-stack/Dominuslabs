"""add customer_name to order_manager_orders

Revision ID: 2026092201
Revises: 2026090701_add_whatsapp_account_tenant_session_unique
Create Date: 2026-09-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2026092201"
down_revision = "2026090701"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_manager_orders",
        sa.Column(
            "customer_name",
            sa.String(255),
            nullable=True,
            server_default="Cliente",
        ),
    )


def downgrade() -> None:
    op.drop_column("order_manager_orders", "customer_name")
