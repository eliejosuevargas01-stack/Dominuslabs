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
        existing.idpw = "123"
        existing.tenant_id = user.tenant_id
        db.commit()
        db.refresh(existing)
        return existing

    account = WhatsappAccount(
        user_id=user.id,
        tenant_id=user.tenant_id,
        idpw="123"
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

    payload = {"name": "test_session", "isDefault": True}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions", json=payload, headers=auth_headers)

    assert response.status_code == 200
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

def test_legacy_credentials_endpoint_eliminated_returns_404(client: TestClient, auth_headers: dict):
    # P0: Completely eliminate legacy client_id/client_secret endpoints
    response_get = client.get(f"{settings.API_V1_STR}/whatsapp/credentials", headers=auth_headers)
    assert response_get.status_code == 404

    payload = {"client_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", "client_secret": "new_secret"}
    response_put = client.put(f"{settings.API_V1_STR}/whatsapp/credentials", json=payload, headers=auth_headers)
    assert response_put.status_code == 404

def test_legacy_provision_endpoint_eliminated_returns_404(client: TestClient, auth_headers: dict):
    # P0: Legacy provisioning endpoint is permanently removed
    response = client.post(f"{settings.API_V1_STR}/whatsapp/provision", headers=auth_headers)
    assert response.status_code == 404

def test_unknown_session_rejected_with_404_across_routes(client: TestClient, auth_headers: dict, test_whatsapp_account):
    # Non-existent session must return 404 without calling upstream WhatsApp API
    res_status = client.get(f"{settings.API_V1_STR}/whatsapp/sessions/unknown-sess-999", headers=auth_headers)
    assert res_status.status_code == 404

    res_conn = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/unknown-sess-999/connect", headers=auth_headers)
    assert res_conn.status_code == 404

    res_disconn = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/unknown-sess-999/disconnect", headers=auth_headers)
    assert res_disconn.status_code == 404

    res_del = client.delete(f"{settings.API_V1_STR}/whatsapp/sessions/unknown-sess-999", headers=auth_headers)
    assert res_del.status_code == 404

    res_msg = client.post(
        f"{settings.API_V1_STR}/whatsapp/sessions/unknown-sess-999/messages/send",
        json={"phone": "5511999999999", "message": "Hi"},
        headers=auth_headers
    )
    assert res_msg.status_code == 404


@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_send_message(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = {"id": "msg_123", "status": "SENT"}

    payload = {"phone": "5511999999999", "message": "Hello", "type": "text"}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/123/messages/send", json=payload, headers=auth_headers)

    assert response.status_code == 200


def test_ram_proxy_no_creds(client: TestClient, auth_headers: dict):
    payload = {"username": "", "password": ""}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/instagram/login", json=payload, headers=auth_headers)
    assert response.status_code == 400

@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_ram_proxy_success(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict):
    mock_get_headers.return_value = {"Authorization": "Bearer token", "x-session-token": "123"}
    mock_api_request.return_value = {"status": "ok"}

    payload = {"username": "user", "password": "password"}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/instagram/login", json=payload, headers=auth_headers)
    assert response.status_code == 200

@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_logout_instagram_proxy(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = {"status": "ok"}

    response = client.post(f"{settings.API_V1_STR}/whatsapp/instagram/sessions/test_user/logout", headers=auth_headers)
    assert response.status_code == 200


def test_resolve_owned_whatsapp_session_blocks_cross_tenant_before_api(db):
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    from app.models.user import User

    user_a = User(
        email="operator_a@tenant-a.com",
        hashed_password="pw",
        tenant_id="tenant_a",
        preferred_session_id="session-a",
        role="custom",
        permissions="read,write"
    )
    user_b = User(
        email="operator_b@tenant-b.com",
        hashed_password="pw",
        tenant_id="tenant_b",
        preferred_session_id="session-b",
        role="custom",
        permissions="read,write"
    )
    db.add(user_a)
    db.add(user_b)
    db.commit()

    # User B trying to access User A's session -> raises 403 Forbidden
    with pytest.raises(Exception) as exc_info:
        resolve_owned_whatsapp_session(user_b, "session-a", db)
    assert exc_info.value.status_code == 403
    assert "Acesso negado" in exc_info.value.detail

    # User B accessing their own session -> succeeds
    session = resolve_owned_whatsapp_session(user_b, "session-b", db)
    assert session == "session-b"


def test_avatar_and_media_proxy_cross_tenant_rejection_before_api_call(db, client):
    from app.models.user import User
    from app.core.auth import create_access_token

    user_a = User(
        email="owner@tenant-a.com",
        hashed_password="pw",
        tenant_id="tenant_a",
        preferred_session_id="session-a",
        role="custom",
        permissions="read,write"
    )
    user_b = User(
        email="attacker@tenant-b.com",
        hashed_password="pw",
        tenant_id="tenant_b",
        preferred_session_id="session-b",
        role="custom",
        permissions="read,write"
    )
    db.add(user_a)
    db.add(user_b)
    db.commit()

    token_b = create_access_token({"sub": user_b.email, "tenant_id": user_b.tenant_id, "role": user_b.role})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    with patch("app.api.endpoints.whatsapp.make_whatsapp_api_request") as mock_api:
        # Endpoint in whatsapp router: /api/v1/whatsapp/sessions/{session_id}/avatar
        res = client.get(
            f"{settings.API_V1_STR}/whatsapp/sessions/session-a/avatar?jid=contact@s.whatsapp.net",
            headers=headers_b
        )
        assert res.status_code == 403
        assert "Acesso negado" in res.json()["detail"]
        mock_api.assert_not_called()

        # Root proxy: /api/sessions/{session_id}/avatar
        res_root = client.get(
            "/api/sessions/session-a/avatar?jid=contact@s.whatsapp.net",
            headers=headers_b
        )
        assert res_root.status_code == 403
        assert "Acesso negado" in res_root.json()["detail"]
        mock_api.assert_not_called()


def test_make_whatsapp_api_request_fails_closed_when_tenant_id_missing():
    import asyncio
    from app.api.endpoints.whatsapp import make_whatsapp_api_request

    # Calling without x-tenant-id must fail closed with 403
    with pytest.raises(Exception) as exc_info:
        asyncio.run(make_whatsapp_api_request("GET", "/test", headers={"Authorization": "Bearer fake"}))
    assert exc_info.value.status_code == 403
    assert "x-tenant-id" in exc_info.value.detail


@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_delete_session_success_cleans_local_account(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, test_whatsapp_account, db):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = {"success": True, "message": "Deleted"}

    response = client.delete(f"{settings.API_V1_STR}/whatsapp/sessions/123", headers=auth_headers)
    assert response.status_code == 200

    acc = db.query(WhatsappAccount).filter(WhatsappAccount.idpw == "123").first()
    assert acc is None


@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_delete_session_idempotent_when_upstream_returns_404(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, test_whatsapp_account, db):
    from fastapi import HTTPException
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.side_effect = HTTPException(status_code=404, detail="Session not found on server")

    response = client.delete(f"{settings.API_V1_STR}/whatsapp/sessions/123", headers=auth_headers)
    assert response.status_code == 200
    assert response.json().get("success") is True

    acc = db.query(WhatsappAccount).filter(WhatsappAccount.idpw == "123").first()
    assert acc is None


@patch("app.api.endpoints.whatsapp.make_whatsapp_api_request")
@patch("app.api.endpoints.whatsapp.get_user_m2m_headers")
def test_list_sessions_auto_syncs_to_local_db(mock_get_headers, mock_api_request, client: TestClient, auth_headers: dict, db):
    mock_get_headers.return_value = {"Authorization": "Bearer token"}
    mock_api_request.return_value = [
        {"id": "3643-principal", "name": "3643 principal", "status": "CONNECTED"}
    ]

    response = client.get(f"{settings.API_V1_STR}/whatsapp/sessions", headers=auth_headers)
    assert response.status_code == 200

    acc_slug = db.query(WhatsappAccount).filter(WhatsappAccount.idpw == "3643-principal").first()
    acc_name = db.query(WhatsappAccount).filter(WhatsappAccount.idpw == "3643 principal").first()
    assert acc_slug is not None
    assert acc_name is not None


def test_resolve_owned_whatsapp_session_matches_slug_and_name_variants(db):
    from app.services.whatsapp_service import resolve_owned_whatsapp_session
    from app.models.user import User

    user = User(
        email="test_variants@tenant.com",
        hashed_password="pw",
        tenant_id="tenant_var",
        role="custom"
    )
    db.add(user)
    db.commit()

    acc = WhatsappAccount(
        user_id=user.id,
        tenant_id=user.tenant_id,
        idpw="3643 principal"
    )
    db.add(acc)
    db.commit()

    resolved = resolve_owned_whatsapp_session(user, "3643-principal", db)
    assert resolved in ("3643 principal", "3643-principal")

    resolved_space = resolve_owned_whatsapp_session(user, "3643 principal", db)
    assert resolved_space in ("3643 principal", "3643-principal")

