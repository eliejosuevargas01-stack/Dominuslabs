"""Update order manager items for n8n contract

Revision ID: 2026090201
Revises: 2026082902
Create Date: 2026-09-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026090201'
down_revision = '2026083001'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('order_manager_order_items', sa.Column('tenant_id', sa.String(length=255), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('pedido_id', sa.String(length=255), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('external_item_id', sa.String(length=255), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('preco_unitario', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('observacoes', sa.String(), nullable=True))
    op.add_column('order_manager_order_items', sa.Column('created_at', sa.DateTime(), nullable=True))

    # Existing rows already belong to a persisted order. Derive the new
    # scoped values from that order instead of creating placeholder tenants.
    op.execute("""
        UPDATE order_manager_order_items AS item
        SET tenant_id = parent.tenant_id,
            pedido_id = parent.pedido_id,
            external_item_id = item.id::text,
            preco_unitario = CASE
                WHEN item.quantidade > 0 THEN item.subtotal / item.quantidade
                ELSE 0
            END,
            created_at = parent.created_at
        FROM order_manager_orders AS parent
        WHERE item.order_id = parent.id
    """)

    op.alter_column('order_manager_order_items', 'tenant_id', nullable=False)
    op.alter_column('order_manager_order_items', 'pedido_id', nullable=False)
    op.alter_column('order_manager_order_items', 'external_item_id', nullable=False)
    op.alter_column('order_manager_order_items', 'preco_unitario', nullable=False)
    op.alter_column('order_manager_order_items', 'created_at', nullable=False)

    op.create_index(op.f('ix_order_manager_order_items_tenant_id'), 'order_manager_order_items', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_order_manager_order_items_pedido_id'), 'order_manager_order_items', ['pedido_id'], unique=False)
    op.create_unique_constraint(
        'uq_order_manager_item_scope_external',
        'order_manager_order_items',
        ['tenant_id', 'pedido_id', 'external_item_id'],
    )

def downgrade():
    op.drop_constraint('uq_order_manager_item_scope_external', 'order_manager_order_items', type_='unique')
    op.drop_index(op.f('ix_order_manager_order_items_pedido_id'), table_name='order_manager_order_items')
    op.drop_index(op.f('ix_order_manager_order_items_tenant_id'), table_name='order_manager_order_items')
    op.drop_column('order_manager_order_items', 'created_at')
    op.drop_column('order_manager_order_items', 'observacoes')
    op.drop_column('order_manager_order_items', 'preco_unitario')
    op.drop_column('order_manager_order_items', 'external_item_id')
    op.drop_column('order_manager_order_items', 'pedido_id')
    op.drop_column('order_manager_order_items', 'tenant_id')
