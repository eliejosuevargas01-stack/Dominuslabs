import pytest

from app.services.n8n_service import N8NService, ProgressiveContactCache


def test_n8n_leads_cache_key_is_scoped_by_tenant_and_user():
    assert N8NService._leads_cache_key("operator@example.com", "tenant-a") != N8NService._leads_cache_key(
        "operator@example.com",
        "tenant-b",
    )
    assert N8NService._leads_cache_key("operator-a@example.com", "tenant-a") != N8NService._leads_cache_key(
        "operator-b@example.com",
        "tenant-a",
    )


def test_n8n_crm_payload_never_falls_back_to_an_admin_tenant():
    with pytest.raises(ValueError, match="tenant_id"):
        N8NService._enrich_payload({"action": "get_contacts"})


def test_progressive_contact_cache_requires_tenant_session_and_contact():
    ProgressiveContactCache.clear()
    try:
        contact_jid = "5511999999999@s.whatsapp.net"
        ProgressiveContactCache.set_messages(
            contact_jid,
            [{"message_id": "a-1", "content": "Sessão A"}],
            session_id="session-a",
            tenant_id="tenant-a",
        )
        ProgressiveContactCache.set_messages(
            contact_jid,
            [{"message_id": "b-1", "content": "Sessão B"}],
            session_id="session-b",
            tenant_id="tenant-b",
        )

        cached_a = ProgressiveContactCache.get_assembled_payload(
            contact_jid,
            session_id="session-a",
            tenant_id="tenant-a",
        )
        cached_b = ProgressiveContactCache.get_assembled_payload(
            contact_jid,
            session_id="session-b",
            tenant_id="tenant-b",
        )

        assert cached_a["messages"][0]["message_id"] == "a-1"
        assert cached_b["messages"][0]["message_id"] == "b-1"
    finally:
        ProgressiveContactCache.clear()
