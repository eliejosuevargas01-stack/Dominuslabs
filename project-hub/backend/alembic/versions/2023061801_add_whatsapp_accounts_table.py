"""add whatsapp_accounts table

Revision ID: 2023061801
Revises: None
Create Date: 2026-06-18 21:47:20.000000
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

# revision identifiers, used by Alembic.
revision = "2023061801"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "whatsapp_accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("client_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("client_secret", sa.String(255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_whatsapp_accounts_user"),
    )
    op.create_index("idx_whatsapp_accounts_user_id", "whatsapp_accounts", ["user_id"])

def downgrade() -> None:
    op.drop_index("idx_whatsapp_accounts_user_id", table_name="whatsapp_accounts")
    op.drop_table("whatsapp_accounts")
