"""Refactor whatsapp_account session_id and drop whatsapp_token

Revision ID: 2026090601
Revises: 2026090201
Create Date: 2026-09-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026090601'
down_revision = '2026090201'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add session_id and display_name columns
    op.add_column('whatsapp_accounts', sa.Column('session_id', sa.String(length=255), nullable=True))
    op.add_column('whatsapp_accounts', sa.Column('display_name', sa.String(length=255), nullable=True))

    # 2. Migrate existing data from idpw to session_id
    op.execute("""
        UPDATE whatsapp_accounts
        SET session_id = idpw
        WHERE idpw IS NOT NULL;
    """)

    # 3. Clean up invalid / legacy placeholder rows (e.g. default or orphan rows)
    op.execute("""
        DELETE FROM whatsapp_accounts
        WHERE session_id IS NULL OR tenant_id IS NULL OR LOWER(session_id) = 'default';
    """)

    # 4. Enforce NOT NULL constraints and index
    op.alter_column('whatsapp_accounts', 'session_id', nullable=False)
    op.alter_column('whatsapp_accounts', 'tenant_id', nullable=False)
    op.create_index(op.f('ix_whatsapp_accounts_session_id'), 'whatsapp_accounts', ['session_id'], unique=False)

    # 5. Drop legacy idpw column
    op.drop_column('whatsapp_accounts', 'idpw')

    # 6. Drop legacy whatsapp_token column from users if present
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'whatsapp_token' in user_columns:
        op.drop_column('users', 'whatsapp_token')


def downgrade() -> None:
    # Add back idpw and whatsapp_token
    op.add_column('whatsapp_accounts', sa.Column('idpw', sa.String(length=255), nullable=True))
    op.execute("UPDATE whatsapp_accounts SET idpw = session_id;")
    op.drop_index(op.f('ix_whatsapp_accounts_session_id'), table_name='whatsapp_accounts')
    op.drop_column('whatsapp_accounts', 'display_name')
    op.drop_column('whatsapp_accounts', 'session_id')
    op.alter_column('whatsapp_accounts', 'tenant_id', nullable=True)

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'whatsapp_token' not in user_columns:
        op.add_column('users', sa.Column('whatsapp_token', sa.String(length=255), nullable=True))
