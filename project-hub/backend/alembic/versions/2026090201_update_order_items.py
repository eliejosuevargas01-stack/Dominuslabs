"""Update order manager items for n8n contract

Revision ID: 2026090201
Revises: 2026082902
Create Date: 2026-09-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '2026090201'
down_revision = '2026082902'
branch_labels = None
depends_on = None

def upgrade():
    # Change 'id' column from UUID to String
    op.alter_column('order_manager_order_items', 'id',
               existing_type=UUID(as_uuid=True),
               type_=sa.String(length=255),
               existing_nullable=False,
               postgresql_using='id::varchar')

    op.add_column('order_manager_order_items', sa.Column('tenant_id', sa.String(length=255), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('pedido_id', sa.String(length=255), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('preco_unitario', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('observacoes', sa.String(), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('created_at', sa.DateTime(), nullable=True))

    op.execute("UPDATE order_manager_order_items SET tenant_id = 'unknown', pedido_id = 'unknown', preco_unitario = 0, created_at = NOW() WHERE tenant_id IS NULL")

    op.alter_column('order_manager_order_items', 'tenant_id', nullable=False)
    op.alter_column('order_manager_order_items', 'pedido_id', nullable=False)
    op.alter_column('order_manager_order_items', 'preco_unitario', nullable=False)
    op.alter_column('order_manager_order_items', 'created_at', nullable=False)

    op.create_index(op.f('ix_order_manager_order_items_tenant_id'), 'order_manager_order_items', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_order_manager_order_items_pedido_id'), 'order_manager_order_items', ['pedido_id'], unique=False)

def downgrade():
    # Revert 'id' column from String back to UUID
    # This might fail on data if it contains non-uuid strings, but since old data is UUID it's fine
    op.alter_column('order_manager_order_items', 'id',
               existing_type=sa.String(length=255),
               type_=UUID(as_uuid=True),
               existing_nullable=False,
               postgresql_using='id::uuid')

    op.drop_index(op.f('ix_order_manager_order_items_pedido_id'), table_name='order_manager_order_items')
    op.drop_index(op.f('ix_order_manager_order_items_tenant_id'), table_name='order_manager_order_items')
    op.drop_column('order_manager_order_items', 'created_at')
    op.drop_column('order_manager_order_items', 'observacoes')
    op.drop_column('order_manager_order_items', 'preco_unitario')
    op.drop_column('order_manager_order_items', 'pedido_id')
    op.drop_column('order_manager_order_items', 'tenant_id')
