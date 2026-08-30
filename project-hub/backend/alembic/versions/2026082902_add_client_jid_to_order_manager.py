"""add client_jid to Order Manager orders

Revision ID: 2026082902
Revises: 2026082901
"""

from alembic import op
import sqlalchemy as sa

revision = "2026082902"
down_revision = "2026082901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_manager_orders", sa.Column("client_jid", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("order_manager_orders", "client_jid")
