from app.core.config import settings

def test_crm_endpoints(client):
    from unittest.mock import patch
    with patch("app.services.n8n_service.n8n_service.get_leads") as mock_get_leads:
        mock_get_leads.return_value = [{"id": "lead-1", "company_name": "Test Company", "status": "frio"}]

        # Get auth token
        login_res = client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test unauthorized listing
        res = client.get("/api/v1/crm/leads")
        assert res.status_code == 401

        # Test authorized listing
        res = client.get("/api/v1/crm/leads", headers=headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) > 0
        first_lead = leads[0]
        assert "company_name" in first_lead
        assert "status" in first_lead
        lead_id = first_lead["id"]

        with patch("app.services.n8n_service.n8n_service.update_lead") as mock_update_lead:
            expected_email = settings.ADMIN_USERNAME if "@" in settings.ADMIN_USERNAME else f"{settings.ADMIN_USERNAME}@dominuslabs.online"
            mock_update_lead.return_value = {
                "id": lead_id,
                "company_name": "Clínica Sorriso Atualizada",
                "notes": "Nova nota de teste",
                "status": "Negociando/Objeção",
                "alterado_por": expected_email,
                "updated_by": expected_email
            }
            # Test updating a lead
            update_payload = {
                "company_name": "Clínica Sorriso Atualizada",
                "notes": "Nova nota de teste",
                "status": "Negociando/Objeção"
            }
            res = client.put(f"/api/v1/crm/leads/{lead_id}", json=update_payload, headers=headers)
            assert res.status_code == 200
            updated_lead = res.json()
            assert updated_lead["company_name"] == "Clínica Sorriso Atualizada"
            assert updated_lead["status"] == "Negociando/Objeção"
            assert updated_lead["alterado_por"] == expected_email
            assert updated_lead["updated_by"] == expected_email

        with patch("app.services.n8n_service.n8n_service.get_messages") as mock_get_messages:
            mock_get_messages.return_value = []
            # Test get conversation messages
            res = client.get(f"/api/v1/crm/conversations/{lead_id}", headers=headers)
    assert res.status_code == 200
    messages = res.json()
    assert isinstance(messages, list)

    # Test send whatsapp message (Success)
    send_payload = {
        "lead_id": lead_id,
        "phone": "+5511999999991",
        "message": "Olá, esta é uma mensagem de teste!",
        "session_id": "test_session"
    }
    from unittest.mock import patch, AsyncMock
    with patch("app.services.whatsapp_service.get_m2m_jwt", new_callable=AsyncMock, return_value="mock_jwt_token"), \
         patch("app.api.endpoints.whatsapp.make_whatsapp_api_request", new_callable=AsyncMock) as mock_wa_req:
        mock_wa_req.return_value = {"status": "success", "message": {"id": "msg_test_123"}}

        res = client.post("/api/v1/crm/messages/send", json=send_payload, headers=headers)
        assert res.status_code == 200
        msg_sent = res.json()
        assert msg_sent["sender"] == "user"
        assert msg_sent["message"] == "Olá, esta é uma mensagem de teste!"

    # Test send whatsapp message (Failure propagation)
    with patch("app.services.whatsapp_service.get_m2m_jwt", new_callable=AsyncMock, return_value="mock_jwt_token"), \
         patch("app.api.endpoints.whatsapp.make_whatsapp_api_request", new_callable=AsyncMock) as mock_wa_req:
        from fastapi import HTTPException
        mock_wa_req.side_effect = HTTPException(status_code=400, detail="O numero informado nao esta registrado no WhatsApp.")

        res = client.post("/api/v1/crm/messages/send", json=send_payload, headers=headers)
        assert res.status_code == 400
        assert "O numero informado nao esta registrado no WhatsApp." in res.json()["detail"]

    # Test get dashboard metrics
    res = client.get("/api/v1/crm/dashboard", headers=headers)
    assert res.status_code == 200
    metrics = res.json()
    assert "total_leads" in metrics
    assert "taxa_conversao" in metrics

    # Test activities timeline
    res = client.get(f"/api/v1/crm/leads/{lead_id}/activities", headers=headers)
    assert res.status_code == 200
    activities = res.json()
    assert isinstance(activities, list)

    # Test create activity
    activity_payload = {
        "event_type": "proposal_opened",
        "metadata": {"amount": 1200}
    }
    res = client.post(f"/api/v1/crm/leads/{lead_id}/activities", json=activity_payload, headers=headers)
    assert res.status_code == 200
    activity_created = res.json()
    assert activity_created["event_type"] == "proposal_opened"
    assert activity_created["lead_id"] == lead_id

def test_scrapper_endpoints(client):
    # Get auth token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test unauthorized scrapper run
    res = client.post("/api/v1/scrapper/run", json={
        "queries": ["Clínicas odontológicas São Paulo"],
        "platforms": ["Google Maps"],
        "min_results": 5,
        "max_results": 20
    })
    assert res.status_code == 401

    # Test authorized scrapper run
    from unittest.mock import patch
    with patch("app.services.n8n_service.n8n_service.run_scrapper", return_value={"status": "success", "message": "Scrapper triggered"}):
        res = client.post("/api/v1/scrapper/run", json={
            "queries": ["Clínicas odontológicas São Paulo"],
            "platforms": ["Google Maps"],
            "min_results": 5,
            "max_results": 20
        }, headers=headers)
        assert res.status_code == 200
        scrapper_result = res.json()
        assert scrapper_result["status"] in ("success", "accepted")

from unittest.mock import patch
from app.services.n8n_service import n8n_service
import pytest

@pytest.mark.anyio
async def test_n8n_double_requests_matching():
    # Setup mock data for leads and messages
    mock_leads_response = [
        {
            "id": 5776,
            "nome_empresa": "Marília Bazzan - Advogada Trabalhista",
            "whatsapp": "5511999999999",
            "status": "frio"
        },
        {
            "id": 5093,
            "nome_empresa": "Dr Carlos Manfrim - Cirurgião Plástico",
            "whatsapp": "554727843106",
            "status": "contatado",
            "updatedAt": "2026-06-10T16:24:38.723Z"
        }
    ]
    
    mock_conversations_response = []
    
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
            
        def json(self):
            return self._json
            
        @property
        def text(self):
            import json
            return json.dumps(self._json)
            
        def raise_for_status(self):
            pass

    async def mock_post(url, *args, **kwargs):
        # When encrypt/decrypt is bypassed via mock, we just return the raw json
        # since it's going to be decrypted, we should mock `decrypt_payload` too.
        # Actually n8n_service.decrypt_payload returns data intact if not encrypted in test env.
        url_str = str(url)
        # N8N service now posts to the same webhook url but with a json payload that includes the action.
        # But wait, in the test CRM_GET_LEADS_WEBHOOK_URL is mocked as "http://test-n8n/webhook".
        # So both get_contacts and get_messages might be calling the same URL.
        # Let's inspect the json argument: kwargs.get('json', {})
        json_payload = kwargs.get("json", {})

        # If encrypt_payload was called, it returns `{"payload": "...", "iv": "..."}` or similar.
        # But in test environment crypto might be missing public keys and return original payload!
        # Log showed: WARNING  crypto:crypto.py:94 No public key found for target: n8n. Returning original payload.
        # So json_payload IS the original payload.
        action = json_payload.get("action", "")

        if "get_contacts" in action or "get_leads" in action:
            return MockResponse(mock_leads_response)
        elif "get_messages" in action or "get_chat_history" in action or "get_conversations" in action:
            return MockResponse(mock_conversations_response)

        # fallback based on URL just in case
        if "get_contacts" in url_str or "get_leads" in url_str:
            return MockResponse(mock_leads_response)
        elif "get_messages" in url_str or "get_chat_history" in url_str or "get_conversations" in url_str:
            return MockResponse(mock_conversations_response)

        return MockResponse([])

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with patch("app.core.config.settings.CRM_GET_LEADS_WEBHOOK_URL", "http://test-n8n/webhook"):
            with patch("app.core.config.settings.CRM_GET_MESSAGES_WEBHOOK_URL", "http://test-n8n/webhook"):
                leads = await n8n_service.get_leads()
                
                # Check that both leads are fetched and combined correctly
                assert len(leads) == 2
                
                # The lead with matching conversations (5093) should have:
                # has_messages=True, mensagem_enviada=True, and should be sorted at the top (index 0)
                assert leads[0]["id"] == "5093"
                assert leads[0]["has_messages"] is True
                assert leads[0]["mensagem_enviada"] is True
                assert leads[0]["last_interaction"] == "2026-06-10T16:24:38.723Z"
                
                # The lead with no conversations (5776) should have:
                # has_messages=False, mensagem_enviada=False, and should be at index 1
                assert leads[1]["id"] == "5776"
                assert leads[1]["has_messages"] is False
                assert leads[1]["mensagem_enviada"] is False


def test_auth_refresh_endpoint(client):
    # Test normal login returns access and refresh tokens
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    assert login_res.status_code == 200
    res_data = login_res.json()
    assert "access_token" in res_data
    assert "refresh_token" in res_data
    refresh_token = res_data["refresh_token"]

    # Test refresh token endpoint with valid token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_res.status_code == 200
    refresh_data = refresh_res.json()
    assert "access_token" in refresh_data
    assert "refresh_token" in refresh_data
    
    # Test that refresh token is rejected for normal endpoint
    bad_headers = {"Authorization": f"Bearer {refresh_token}"}
    res = client.get("/api/v1/crm/leads", headers=bad_headers)
    assert res.status_code == 401

    # Test invalid refresh token
    bad_refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_refresh_token_string"}
    )
    assert bad_refresh_res.status_code == 401

def test_n8n_raw_mapping_service():
    from app.services.n8n_service import map_n8n_lead, update_raw_lead, RAW_LEADS_CACHE
    import copy

    mock_n8n_lead = {
        "lead_id": "meta_999888",
        "origem": "meta_ads_library",
        "status": "Prospectado",
        "empresa_nome": "Sorveteria Delícia",
        "payload": {
            "tem_cta": "não",
            "tem_site_proprio": False
        }
    }

    mapped = map_n8n_lead(mock_n8n_lead)
    assert "meta_999888" in RAW_LEADS_CACHE

    cached = RAW_LEADS_CACHE["meta_999888"]
    frontend_payload = {
        "company_name": "Sorveteria Delícia Atualizada",
        "status": "Negociando/Objeção",
        "presenca_digital_tem_cta": "sim",
        "tem_site_proprio": True,
        "localizacao": "Curitiba"
    }

    outgoing = update_raw_lead(cached, frontend_payload)
    assert outgoing["empresa_nome"] == "Sorveteria Delícia Atualizada"
    assert outgoing["status"] == "Negociando/Objeção"
    assert outgoing["payload"]["tem_cta"] == "sim"
    assert outgoing["payload"]["tem_site_proprio"] is True
    assert "localizacao" not in outgoing


def test_crm_chat_update_sse_webhook(client):
    # Add a mock queue listener manually to lead_listeners to mock an active session
    from app.api.endpoints.webhooks import lead_listeners
    import asyncio
    queue = asyncio.Queue()
    lead_listeners["test_lead_listener"] = [("admin@dominuslabs.online", queue)]

    from unittest.mock import patch
    with patch("app.services.n8n_service.n8n_service.get_messages") as mock_get_messages:
        mock_get_messages.return_value = []
        payload_2 = [{
            "message_id": "msg-124",
            "contact_jid": "test_lead_listener",
            "lead_id": "test_lead_listener",
            "session_id": "sess-1",
            "tenant_id": "tenant-1",
            "is_from_me": False,
            "content": "Test msg",
            "timestamp": "2026-08-13T00:00:00Z",
            "status": "delivered",
            "id": "msg-124"
        }]
        res = client.post("/api/v1/webhooks/crm/update-chat?lead_id=test_lead_listener", json=payload_2)
        assert res.status_code == 200

def test_crm_chat_update_global_sse(client):
    from app.api.endpoints.webhooks import crm_chat_listeners
    import asyncio
    queue = asyncio.Queue()
    crm_chat_listeners.append(("admin@dominuslabs.online", queue))

    from unittest.mock import patch
    with patch("app.services.n8n_service.n8n_service.get_messages") as mock_get_messages:
        mock_get_messages.return_value = []
        payload = [{
            "message_id": "msg-125",
            "contact_jid": "test_global_update",
            "lead_id": "test_global_update",
            "session_id": "sess-1",
            "tenant_id": "tenant-1",
            "is_from_me": False,
            "content": "Test msg",
            "timestamp": "2026-08-13T00:00:00Z",
            "status": "delivered",
            "id": "msg-125",
        }]
        res = client.post("/api/v1/webhooks/crm/update-chat", json=payload)
        assert res.status_code == 200

def test_progressive_contact_cache_flow():
    from app.services.n8n_service import ProgressiveContactCache
    ProgressiveContactCache.clear()
    jid = "5511999998888@lid"

    # Request 1: Basic Info (contacts table)
    ProgressiveContactCache.set_contact(jid, {
        "push_name": "Maria Silva",
        "profile_pic_url": "https://img.com/avatar.jpg",
        "display_phone": "+55 (11) 99999-8888"
    })
    profile = ProgressiveContactCache.get(jid)
    assert profile["push_name"] == "Maria Silva"
    assert profile["display_phone"] == "+55 (11) 99999-8888"

    # Request 2: Inbox State (conversations table)
    ProgressiveContactCache.set_conversation(jid, {
        "session_id": "eliezer-sc",
        "unread_count": 3,
        "last_message_preview": "Olá, tudo bem?"
    })
    profile = ProgressiveContactCache.get(jid)
    assert profile["session_id"] == "eliezer-sc"
    assert profile["unread_count"] == 3
    assert profile["last_message_preview"] == "Olá, tudo bem?"
    assert profile["push_name"] == "Maria Silva" # Preserved

    # Request 3: Chat History (messages table)
    msgs = [
        {"id": "m1", "content": "Olá", "is_from_me": False, "timestamp": "2026-08-13T00:00:00Z"},
        {"id": "m2", "content": "Olá, tudo bem?", "is_from_me": True, "timestamp": "2026-08-13T00:01:00Z"}
    ]
    ProgressiveContactCache.set_messages(jid, msgs)

    assembled = ProgressiveContactCache.get_assembled_payload(jid)
    assert assembled["contact_jid"] == jid
    assert assembled["push_name"] == "Maria Silva"
    assert assembled["session_id"] == "eliezer-sc"
    assert len(assembled["mensagens"]) == 2




