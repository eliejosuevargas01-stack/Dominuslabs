"""modify whatsapp_accounts table

Revision ID: 2024082601
Revises: 2023061801
Create Date: 2024-08-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2024082601'
down_revision = '2023061801'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add new columns
    op.add_column('whatsapp_accounts', sa.Column('tenant_id', sa.String(length=255), nullable=True))
    op.add_column('whatsapp_accounts', sa.Column('idpw', sa.String(length=255), nullable=True))

    # Drop old columns
    op.drop_column('whatsapp_accounts', 'client_secret')
    op.drop_column('whatsapp_accounts', 'client_id')

def downgrade() -> None:
    # Add back old columns
    op.add_column('whatsapp_accounts', sa.Column('client_id', postgresql.UUID(as_uuid=True), autoincrement=False, nullable=False))
    op.add_column('whatsapp_accounts', sa.Column('client_secret', sa.VARCHAR(length=255), autoincrement=False, nullable=False))

    # Drop new columns
    op.drop_column('whatsapp_accounts', 'idpw')
    op.drop_column('whatsapp_accounts', 'tenant_id')
