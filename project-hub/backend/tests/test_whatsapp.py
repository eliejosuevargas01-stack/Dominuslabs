import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.auth import create_access_token
from app.models.whatsapp_account import WhatsappAccount

@pytest.fixture
def auth_headers(db):
    from app.repositories.user_repo import user_repo
    admin_email = settings.ADMIN_USERNAME
    if "@" not in admin_email:
        admin_email = f"{settings.ADMIN_USERNAME}@dominuslabs.online"

    user = user_repo.get_by_email(db, admin_email)
    token = create_access_token({
        "sub": user.email,
        "user_id": str(user.id),
        "role": user.role,
        "permissions": user.permissions,
        "tenant_id": user.tenant_id
    })
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_whatsapp_account(db):
    from app.repositories.user_repo import user_repo
    admin_email = settings.ADMIN_USERNAME
    if "@" not in admin_email:
        admin_email = f"{settings.ADMIN_USERNAME}@dominuslabs.online"

    user = user_repo.get_by_email(db, admin_email)

    existing = db.query(WhatsappAccount).filter(WhatsappAccount.user_id == user.id).first()
    if existing:
        return existing

    account = WhatsappAccount(
        user_id=user.id,
        tenant_id=user.tenant_id,
        idpw="test_idpw"
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_list_sessions(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = []

    response = client.get(f"{settings.API_V1_STR}/whatsapp/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_create_session(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = {"id": "123", "status": "CREATED"}

    payload = {"sessionName": "test_session", "isDefault": True}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions", json=payload, headers=auth_headers)

    assert response.status_code in [200, 400]
    if response.status_code == 200:
        assert "status" in response.json()

@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_connect_session(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = {"status": "CONNECTING"}

    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/123/connect", headers=auth_headers)
    assert response.status_code == 200

@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_disconnect_session(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = {"status": "DISCONNECTED"}

    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/123/disconnect", headers=auth_headers)
    assert response.status_code == 200

def test_get_credentials(client: TestClient, auth_headers: dict, test_whatsapp_account):
    response = client.get(f"{settings.API_V1_STR}/whatsapp/credentials", headers=auth_headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data.get("configured") is True
    assert res_data.get("client_id") == "test_idpw"
    assert "client_secret_preview" in res_data

def test_save_credentials(client: TestClient, auth_headers: dict, test_whatsapp_account):
    payload = {
        "client_id": "new_idpw",
        "client_secret": "new_secret"
    }
    response = client.put(f"{settings.API_V1_STR}/whatsapp/credentials", json=payload, headers=auth_headers)
    assert response.status_code in [200, 400, 422]
    if response.status_code == 200:
        assert response.json().get("status") == "success"

@patch("app.services.whatsapp_service.get_tenant_id_for_user")
@patch("app.api.endpoints.whatsapp.get_async_client")
def test_provision_whatsapp(mock_get_async_client, mock_get_tenant_id, client: TestClient, auth_headers: dict):
    mock_get_tenant_id.return_value = "admin"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "client_id": "mock_id", "client_secret": "mock_secret"}

    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_get_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)

    with patch.object(settings, 'WHATSAPP_MASTER_SECRET', 'test_secret'):
        response = client.post(f"{settings.API_V1_STR}/whatsapp/provision", headers=auth_headers)

    assert response.status_code == 200
