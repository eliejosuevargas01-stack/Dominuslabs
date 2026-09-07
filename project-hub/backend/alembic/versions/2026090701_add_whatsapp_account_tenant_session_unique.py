"""Add unique constraint on whatsapp_accounts (tenant_id, session_id)

Revision ID: 2026090701
Revises: 2026090601
Create Date: 2026-09-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026090701'
down_revision = '2026090601'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Deduplicate any existing records having identical (tenant_id, session_id), keeping the latest ID
    op.execute("""
        DELETE FROM whatsapp_accounts
        WHERE id NOT IN (
            SELECT max_id FROM (
                SELECT MAX(id) AS max_id
                FROM whatsapp_accounts
                GROUP BY tenant_id, session_id
            ) AS t
        );
    """)

    # 2. Add compound unique constraint on (tenant_id, session_id)
    op.create_unique_constraint(
        "uq_whatsapp_accounts_tenant_session",
        "whatsapp_accounts",
        ["tenant_id", "session_id"]
    )


def downgrade() -> None:
    # Drop compound unique constraint
    op.drop_constraint(
        "uq_whatsapp_accounts_tenant_session",
        "whatsapp_accounts",
        type_="unique"
    )
