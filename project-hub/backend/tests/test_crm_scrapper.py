from app.core.config import settings

def test_crm_endpoints(client):
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

    # Test get conversation messages
    res = client.get(f"/api/v1/crm/conversations/{lead_id}", headers=headers)
    assert res.status_code == 200
    messages = res.json()
    assert isinstance(messages, list)

    # Test send whatsapp message (Success)
    send_payload = {
        "lead_id": lead_id,
        "phone": "+5511999999991",
        "message": "Olá, esta é uma mensagem de teste!"
    }
    from unittest.mock import patch
    with patch("httpx.AsyncClient.post") as mock_post:
        class MockResponse:
            status_code = 200
            def json(self):
                return {"status": "success", "message": "Message sent"}
            @property
            def text(self):
                return '{"status": "success", "message": "Message sent"}'
        mock_post.return_value = MockResponse()

        res = client.post("/api/v1/crm/messages/send", json=send_payload, headers=headers)
        assert res.status_code == 200
        msg_sent = res.json()
        assert msg_sent["sender"] == "user"
        assert msg_sent["message"] == "Olá, esta é uma mensagem de teste!"

    # Test send whatsapp message (Failure propagation)
    with patch("httpx.AsyncClient.post") as mock_post:
        class MockFailedResponse:
            status_code = 400
            def json(self):
                return {"error": "bad_request", "message": "O numero informado nao esta registrado no WhatsApp."}
            @property
            def text(self):
                return '{"error": "bad_request", "message": "O numero informado nao esta registrado no WhatsApp."}'
        mock_post.return_value = MockFailedResponse()

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

    async def mock_get(url, *args, **kwargs):
        if "action=get_leads" in url:
            return MockResponse(mock_leads_response)
        elif "action=get_messages" in url:
            return MockResponse(mock_conversations_response)
        return MockResponse([])

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
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
    # Test update-chat endpoint with no active listeners
    res = client.post("/api/v1/webhooks/crm/update-chat", json={"lead_id": "test_lead_no_listener"})
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"

    # Add a mock queue listener manually to lead_listeners to mock an active session
    from app.api.endpoints.webhooks import lead_listeners
    import asyncio
    queue = asyncio.Queue()
    lead_listeners["test_lead_listener"] = [("admin@dominuslabs.online", queue)]

    # Mock the n8n_service.get_messages call
    from unittest.mock import patch
    with patch("app.services.n8n_service.n8n_service.get_messages") as mock_get_messages:
        mock_get_messages.return_value = []
        
        # Test update-chat endpoint with active listener
        res = client.post("/api/v1/webhooks/crm/update-chat", json={"lead_id": "test_lead_listener"})
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        assert res.json()["notified_sessions"] == 1
        
        # Verify event "reload" was pushed to the queue
        assert queue.get_nowait() == "reload"

    # Clean up
    if "test_lead_listener" in lead_listeners:
        del lead_listeners["test_lead_listener"]



