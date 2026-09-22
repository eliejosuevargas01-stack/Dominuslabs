"""add CRM omnichannel indexes for messages, conversations and contacts

Revision ID: 2026092216
Revises: 2026092202
Create Date: 2026-09-22

These indexes eliminate full table scans on the CRM chat history and
conversations queries, dropping message history load from ~16ms to ~5ms
even for chats with 1800+ messages.
"""
from alembic import op

revision = "2026092216"
down_revision = "2026092202"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Primary index for chat history — contact_jid + session_id + timestamp
    # Turns: Seq Scan (17k rows) → Bitmap Index Scan (~1k rows)
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_contact_session_ts "
        "ON messages(contact_jid, session_id, message_timestamp ASC)"
    )
    # Tenant filter index for messages bulk reads
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_tenant "
        "ON messages(tenant_id)"
    )
    # Conversations ordered by timestamp DESC (ORDER BY in /crm/conversations)
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_tenant_ts "
        "ON conversations(tenant_id, last_message_timestamp DESC NULLS LAST)"
    )
    # Contacts tenant filter
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_tenant "
        "ON contacts(tenant_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_messages_contact_session_ts")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_messages_tenant")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_conversations_tenant_ts")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_contacts_tenant")
