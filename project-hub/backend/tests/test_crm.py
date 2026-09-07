import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user, check_crm_permission, check_admin_role
from app.models.user import User
from app.core.database import get_db
from app.schemas.crm import Lead

client = TestClient(app)

def mock_get_current_user():
    return "test@dominuslabs.online"

def mock_check_crm_permission():
    return "test@dominuslabs.online"

app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[check_crm_permission] = mock_check_crm_permission

@pytest.fixture
def mock_db():
    db = MagicMock()
    user_mock = User(
        id=1,
        email="test@dominuslabs.online",
        tenant_id="tenant_crm_test",
        role="admin",
        preferred_session_id="session1"
    )
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_first = MagicMock(return_value=user_mock)

    mock_filter.first = mock_first
    mock_query.filter.return_value = mock_filter
    db.query.return_value = mock_query

    return db

@patch("app.api.endpoints.crm.n8n_service.get_leads", new_callable=AsyncMock)
def test_get_leads(mock_get_leads, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: "test@dominuslabs.online"
    mock_get_leads.return_value = [{"id": "1", "empresa_nome": "Lead 1", "status": "Prospectado"}]

    response = client.get("/api/v1/crm/leads")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "1"
    mock_get_leads.assert_called_once()


@patch("app.api.endpoints.crm.n8n_service.get_conversations", new_callable=AsyncMock)
def test_get_conversations(mock_get_conversations, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: "test@dominuslabs.online"
    mock_get_conversations.return_value = [{"id": "1", "unread_count": 0, "lead_id": "1", "contact_name": "L", "contact_phone": "123", "last_message": "hi", "last_message_time": "now", "status": "open"}]

    response = client.get("/api/v1/crm/conversations")
    assert response.status_code == 200
    assert response.json() == [{"id": "1", "unread_count": 0, "lead_id": "1", "contact_name": "L", "contact_phone": "123", "last_message": "hi", "last_message_time": "now", "status": "open"}]
    mock_get_conversations.assert_called_once()

@patch("app.api.endpoints.crm.n8n_service.get_messages", new_callable=AsyncMock)
def test_get_chat_history(mock_get_messages, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: "test@dominuslabs.online"
    mock_get_messages.return_value = [{"id": "msg1", "sender": "user", "message": "Hello", "channel": "whatsapp", "timestamp": "now"}]

    response = client.get("/api/v1/crm/chat-history/123")
    assert response.status_code == 200
    assert response.json() == [{"id": "msg1", "sender": "user", "message": "Hello", "channel": "whatsapp", "timestamp": "now"}]
    mock_get_messages.assert_called_once()

@patch("app.api.endpoints.crm.send_whatsapp_message", new_callable=AsyncMock)
def test_send_message(mock_send_whatsapp_message, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_crm_permission] = lambda: "test@dominuslabs.online"
    # mock_send_whatsapp_message must return what crm.py expects
    mock_send_whatsapp_message.return_value = {"message": {"id": "msg1"}}

    payload = {
        "lead_id": "lead_123",
        "contact_jid": "5511999999999@s.whatsapp.net",
        "message": "Test message",
        "session_id": "session1"
    }

    response = client.post("/api/v1/crm/messages/send", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Test message"
    assert "msg1" in response.json()["id"] or "msg_" in response.json()["id"]
    mock_send_whatsapp_message.assert_called_once()

@patch("app.api.endpoints.crm.n8n_service.get_leads", new_callable=AsyncMock)
def test_get_contacts(mock_get_leads, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: "test@dominuslabs.online"
    mock_get_leads.return_value = [{
        "id": "c1",
        "contact_jid": "contact@s.whatsapp.net",
        "nome": "Contact 1",
    }]

    response = client.get("/api/v1/crm/contacts")

    assert response.status_code == 200
    assert response.json()[0]["contact_jid"] == "contact@s.whatsapp.net"
    assert response.json()[0]["push_name"] == "Contact 1"


def test_map_n8n_lead_rejects_tenant_mismatch():
    from app.services.n8n_service import map_n8n_lead, SecurityTenantMismatchError

    # Lead claiming tenant-b when caller expected tenant-a
    malicious_lead = {
        "id": "lead_cross_tenant_1",
        "tenant_id": "tenant-b",
        "nome": "Cliente confidencial do Tenant B"
    }

    with pytest.raises(SecurityTenantMismatchError) as exc_info:
        map_n8n_lead(malicious_lead, tenant_id="tenant-a")
    
    assert "SECURITY_TENANT_MISMATCH" in str(exc_info.value)
    assert "tenant-b" in str(exc_info.value)
    assert "tenant-a" in str(exc_info.value)


def test_map_n8n_message_rejects_tenant_mismatch():
    from app.services.n8n_service import map_n8n_message, SecurityTenantMismatchError

    # Message claiming tenant-b when caller expected tenant-a
    malicious_msg = {
        "message_id": "msg_cross_1",
        "tenant_id": "tenant-b",
        "contact_jid": "5511999999999@s.whatsapp.net",
        "content": "Mensagem secreta do Tenant B"
    }

    with pytest.raises(SecurityTenantMismatchError) as exc_info:
        map_n8n_message(malicious_msg, tenant_id="tenant-a")

    assert "SECURITY_TENANT_MISMATCH" in str(exc_info.value)

    # Nested message in array claiming tenant-b
    nested_malicious_msg = {
        "tenant_id": "tenant-a",
        "mensagens": [
            {
                "id": "msg_nested_cross_1",
                "tenant_id": "tenant-b",
                "content": "Mensagem aninhada cross-tenant"
            }
        ]
    }

    with pytest.raises(SecurityTenantMismatchError) as exc_info_nested:
        map_n8n_message(nested_malicious_msg, tenant_id="tenant-a")

    assert "SECURITY_TENANT_MISMATCH" in str(exc_info_nested.value)


@pytest.mark.anyio
async def test_get_leads_drops_cross_tenant_items_from_n8n():
    from app.services.n8n_service import N8NService

    mixed_leads_payload = [
        {"id": "lead_a1", "tenant_id": "tenant-a", "nome": "Lead Legítimo A"},
        {"id": "lead_b1", "tenant_id": "tenant-b", "nome": "Lead Vazado B"},
        {"id": "lead_a2", "nome": "Lead Sem Tenant Explícito (Herdado)"}
    ]

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mixed_leads_payload
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Call get_leads for tenant-a
        N8NService.invalidate_leads_cache("tenant-a")
        results = await N8NService.get_leads(user_id="user_a", tenant_id="tenant-a")

        # Must contain only lead_a1 and lead_a2; lead_b1 MUST be dropped
        result_ids = [l["id"] for l in results]
        assert "lead_a1" in result_ids
        assert "lead_a2" in result_ids
        assert "lead_b1" not in result_ids

        # Ensure all returned leads have tenant_id == "tenant-a"
        for l in results:
            assert l["tenant_id"] == "tenant-a"


@pytest.mark.anyio
async def test_get_conversations_drops_cross_tenant_items_from_n8n():
    from app.services.n8n_service import N8NService

    mixed_convs_payload = {
        "conversations": [
            {"id": "conv_a1", "contact_jid": "55111111@s.whatsapp.net", "tenant_id": "tenant-a", "nome": "Conv A"},
            {"id": "conv_b1", "contact_jid": "55222222@s.whatsapp.net", "tenant_id": "tenant-b", "nome": "Conv B"}
        ]
    }

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mixed_convs_payload
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        results = await N8NService.get_conversations(user_id="user_a", tenant_id="tenant-a")
        result_ids = [c["id"] for c in results]
        assert "55111111@s.whatsapp.net" in result_ids
        assert "55222222@s.whatsapp.net" not in result_ids
        for c in results:
            assert c["tenant_id"] == "tenant-a"


@pytest.mark.anyio
async def test_get_messages_drops_cross_tenant_messages():
    from app.services.n8n_service import N8NService, RAW_LEADS_CACHE

    RAW_LEADS_CACHE.clear()
    mixed_messages_payload = {
        "messages": [
            {"id": "msg_a", "tenant_id": "tenant-a", "content": "Oi tenant A", "session_id": "sess_a"},
            {"id": "msg_b", "tenant_id": "tenant-b", "content": "Oi tenant B", "session_id": "sess_b"}
        ]
    }

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"dummy": true}'
        mock_response.json.return_value = mixed_messages_payload
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        results = await N8NService.get_messages("5511999999999@s.whatsapp.net", user_id="user_a", tenant_id="tenant-a")
        result_ids = [m["id"] for m in results]
        assert "msg_a" in result_ids
        assert "msg_b" not in result_ids


@pytest.mark.anyio
async def test_get_leads_without_n8n_uses_only_tenant_validated_cache(monkeypatch):
    from app.core.config import settings
    from app.services.n8n_service import N8NService

    monkeypatch.setattr(settings, "CRM_GET_LEADS_WEBHOOK_URL", "")
    N8NService._leads_cache.clear()
    N8NService._leads_cache["tenant-a"] = {
        "data": [{"id": "lead-a", "tenant_id": "tenant-a"}],
        "time": 0.0,
        "url": "https://previously-validated.example/webhook",
    }
    N8NService._leads_cache["tenant-b"] = {
        "data": [{"id": "lead-b", "tenant_id": "tenant-b"}],
        "time": 0.0,
        "url": "https://previously-validated.example/webhook",
    }

    result = await N8NService.get_leads(user_id="user-a", tenant_id="tenant-a")
    result[0]["id"] = "mutated-copy"

    assert N8NService._leads_cache["tenant-a"]["data"][0]["id"] == "lead-a"
    assert all(lead["tenant_id"] == "tenant-a" for lead in N8NService._leads_cache["tenant-a"]["data"])
    N8NService._leads_cache.clear()


@pytest.mark.anyio
async def test_lead_operations_fail_closed_when_n8n_is_not_configured(monkeypatch):
    from app.core.config import settings
    from app.services.n8n_service import (
        MOCK_CONVERSATIONS,
        N8NIntegrationUnavailableError,
        N8NService,
        RAW_LEADS_CACHE,
    )

    tenant_id = "tenant-without-integration"
    lead_id = "lead-preserved"
    cache_key = f"{tenant_id}:{lead_id}"
    monkeypatch.setattr(settings, "CRM_GET_LEADS_WEBHOOK_URL", "")
    monkeypatch.setattr(settings, "CRM_UPDATE_LEAD_WEBHOOK_URL", "")
    N8NService._leads_cache.clear()
    RAW_LEADS_CACHE[cache_key] = {"id": lead_id, "tenant_id": tenant_id}
    MOCK_CONVERSATIONS[cache_key] = [{"id": "message-preserved"}]

    with pytest.raises(N8NIntegrationUnavailableError):
        await N8NService.get_leads(user_id="user-a", tenant_id=tenant_id)
    with pytest.raises(N8NIntegrationUnavailableError):
        await N8NService.update_lead(
            lead_id,
            {"status": "Qualificado"},
            current_user="user-a",
            tenant_id=tenant_id,
        )
    with pytest.raises(N8NIntegrationUnavailableError):
        await N8NService.delete_lead(lead_id, user_id="user-a", tenant_id=tenant_id)

    assert RAW_LEADS_CACHE[cache_key]["id"] == lead_id
    assert MOCK_CONVERSATIONS[cache_key][0]["id"] == "message-preserved"
    RAW_LEADS_CACHE.pop(cache_key, None)
    MOCK_CONVERSATIONS.pop(cache_key, None)


@patch("app.api.endpoints.crm.n8n_service.get_leads", new_callable=AsyncMock)
def test_crm_leads_returns_503_when_integration_is_unavailable(mock_get_leads, mock_db):
    from app.services.n8n_service import N8NIntegrationUnavailableError

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: "test@dominuslabs.online"
    mock_get_leads.side_effect = N8NIntegrationUnavailableError("Integração CRM indisponível.")

    response = client.get("/api/v1/crm/leads")

    assert response.status_code == 503
    assert response.json()["detail"] == "Integração CRM indisponível."
