import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.core.config import settings
from app.core.auth import create_access_token
from app.models.whatsapp_account import WhatsappAccount
from app.models.user import User

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
        existing.session_id = "123"
        existing.tenant_id = user.tenant_id
        db.commit()
        db.refresh(existing)
        return existing

    account = WhatsappAccount(
        user_id=user.id,
        tenant_id=user.tenant_id,
        session_id="123"
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@patch("app.services.whatsapp_client.whatsapp_client.list_sessions", new_callable=AsyncMock)
def test_list_sessions(mock_list, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_list.return_value = []

    response = client.get(f"{settings.API_V1_STR}/whatsapp/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@patch("app.services.whatsapp_client.whatsapp_client.create_session", new_callable=AsyncMock)
def test_create_session(mock_create, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_create.return_value = {"id": "123", "status": "CREATED"}

    payload = {"name": "test_session", "isDefault": True}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions", json=payload, headers=auth_headers)

    assert response.status_code == 200
    assert "status" in response.json()


@patch("app.services.whatsapp_client.whatsapp_client.connect_session", new_callable=AsyncMock)
def test_connect_session(mock_connect, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_connect.return_value = {"status": "CONNECTING"}

    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/123/connect", headers=auth_headers)
    assert response.status_code == 200


@patch("app.services.whatsapp_client.whatsapp_client.disconnect_session", new_callable=AsyncMock)
def test_disconnect_session(mock_disconnect, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_disconnect.return_value = {"status": "DISCONNECTED"}

    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/123/disconnect", headers=auth_headers)
    assert response.status_code == 200


def test_legacy_credentials_endpoint_eliminated_returns_404(client: TestClient, auth_headers: dict):
    response_get = client.get(f"{settings.API_V1_STR}/whatsapp/credentials", headers=auth_headers)
    assert response_get.status_code == 404

    payload = {"client_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", "client_secret": "new_secret"}
    response_put = client.put(f"{settings.API_V1_STR}/whatsapp/credentials", json=payload, headers=auth_headers)
    assert response_put.status_code == 404


def test_legacy_provision_endpoint_eliminated_returns_404(client: TestClient, auth_headers: dict):
    response = client.post(f"{settings.API_V1_STR}/whatsapp/provision", headers=auth_headers)
    assert response.status_code == 404


def test_unknown_session_rejected_with_404_across_routes(client: TestClient, auth_headers: dict, test_whatsapp_account):
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


@patch("app.services.whatsapp_client.whatsapp_client.send_message", new_callable=AsyncMock)
def test_send_message(mock_send, client: TestClient, auth_headers: dict, test_whatsapp_account):
    mock_send.return_value = {"id": "msg_123", "status": "SENT"}

    payload = {"phone": "5511999999999", "message": "Hello", "type": "text"}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/sessions/123/messages/send", json=payload, headers=auth_headers)

    assert response.status_code == 200


def test_ram_proxy_no_creds(client: TestClient, auth_headers: dict):
    payload = {"username": "", "password": ""}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/instagram/login", json=payload, headers=auth_headers)
    assert response.status_code == 400


@patch("app.services.whatsapp_client.whatsapp_client.instagram_login", new_callable=AsyncMock)
def test_ram_proxy_success(mock_login, client: TestClient, auth_headers: dict):
    mock_login.return_value = {"status": "ok"}

    payload = {"username": "user", "password": "password"}
    response = client.post(f"{settings.API_V1_STR}/whatsapp/instagram/login", json=payload, headers=auth_headers)
    assert response.status_code == 200


@patch("app.services.whatsapp_client.whatsapp_client.instagram_logout", new_callable=AsyncMock)
def test_logout_instagram_proxy(mock_logout, client: TestClient, auth_headers: dict):
    mock_logout.return_value = {"status": "ok"}

    response = client.post(f"{settings.API_V1_STR}/whatsapp/instagram/sessions/test_user/logout", headers=auth_headers)
    assert response.status_code == 200


def test_resolve_owned_whatsapp_session_blocks_cross_tenant_before_api(db):
    from app.services.whatsapp_service import resolve_owned_whatsapp_session

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

    acc_a = WhatsappAccount(
        user_id=user_a.id,
        tenant_id="tenant_a",
        session_id="session-a"
    )
    acc_b = WhatsappAccount(
        user_id=user_b.id,
        tenant_id="tenant_b",
        session_id="session-b"
    )
    db.add(acc_a)
    db.add(acc_b)
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

    acc_a = WhatsappAccount(
        user_id=user_a.id,
        tenant_id="tenant_a",
        session_id="session-a"
    )
    db.add(acc_a)
    db.commit()

    token_b = create_access_token({"sub": user_b.email, "tenant_id": user_b.tenant_id, "role": user_b.role})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    with patch("app.services.whatsapp_client.whatsapp_client.get_session_avatar", new_callable=AsyncMock) as mock_api:
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


def test_whatsapp_client_fails_closed_when_tenant_id_missing():
    import asyncio
    from app.services.whatsapp_client import whatsapp_client

    # Calling without tenant_id must fail closed with 403
    with pytest.raises(Exception) as exc_info:
        asyncio.run(whatsapp_client._execute_request(
            method="GET",
            path="/test",
            tenant_id="",
            scope="whatsapp:sessions:read"
        ))
    assert exc_info.value.status_code == 403
    assert "tenant_id" in exc_info.value.detail


@patch("app.services.whatsapp_client.whatsapp_client.delete_session", new_callable=AsyncMock)
def test_delete_session_success_cleans_local_account(mock_del, client: TestClient, auth_headers: dict, test_whatsapp_account, db):
    mock_del.return_value = {"success": True, "message": "Deleted"}

    response = client.delete(f"{settings.API_V1_STR}/whatsapp/sessions/123", headers=auth_headers)
    assert response.status_code == 200

    acc = db.query(WhatsappAccount).filter(WhatsappAccount.session_id == "123").first()
    assert acc is None


@patch("app.services.whatsapp_client.whatsapp_client.delete_session", new_callable=AsyncMock)
def test_delete_session_idempotent_when_upstream_returns_404(mock_del, client: TestClient, auth_headers: dict, test_whatsapp_account, db):
    mock_del.side_effect = HTTPException(status_code=404, detail="Session not found on server")

    response = client.delete(f"{settings.API_V1_STR}/whatsapp/sessions/123", headers=auth_headers)
    assert response.status_code == 200
    assert response.json().get("success") is True

    acc = db.query(WhatsappAccount).filter(WhatsappAccount.session_id == "123").first()
    assert acc is None


@patch("app.services.whatsapp_client.whatsapp_client.list_sessions", new_callable=AsyncMock)
def test_list_sessions_auto_syncs_to_local_db(mock_list, client: TestClient, auth_headers: dict, db):
    mock_list.return_value = [
        {"id": "3643-principal", "name": "3643 principal", "status": "CONNECTED"}
    ]

    response = client.get(f"{settings.API_V1_STR}/whatsapp/sessions", headers=auth_headers)
    assert response.status_code == 200

    acc_slug = db.query(WhatsappAccount).filter(WhatsappAccount.session_id == "3643-principal").first()
    acc_name = db.query(WhatsappAccount).filter(WhatsappAccount.session_id == "3643 principal").first()
    assert acc_slug is not None
    assert acc_name is not None


def test_resolve_owned_whatsapp_session_matches_slug_and_name_variants(db):
    from app.services.whatsapp_service import resolve_owned_whatsapp_session

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
        session_id="3643 principal"
    )
    db.add(acc)
    db.commit()

    resolved = resolve_owned_whatsapp_session(user, "3643-principal", db)
    assert resolved in ("3643 principal", "3643-principal")

    resolved_space = resolve_owned_whatsapp_session(user, "3643 principal", db)
    assert resolved_space in ("3643 principal", "3643-principal")


def test_resolve_owned_whatsapp_session_rejects_session_only_in_preferred_session_id(db):
    """Garante que ter preferred_session_id sem WhatsappAccount no banco não confere ownership (sem fallback)."""
    from app.services.whatsapp_service import resolve_owned_whatsapp_session

    user = User(
        email="unregistered_pref@tenant.com",
        hashed_password="pw",
        tenant_id="tenant_pref_only",
        preferred_session_id="ghost_session_123",
        role="custom"
    )
    db.add(user)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        resolve_owned_whatsapp_session(user, "ghost_session_123", db)
    assert exc_info.value.status_code == 404
    assert "não encontrada" in exc_info.value.detail


def test_crm_avatar_and_media_proxy_reject_anonymous(client):
    """Garante que endpoints proxy de avatar e mídia exigem autenticação do Dominus e rejeitam anônimos com 401."""
    res_avatar = client.get("/api/crm/avatar?session_id=sess1&jid=contact@s.whatsapp.net")
    assert res_avatar.status_code == 401

    res_media = client.get("/api/crm/media?session_id=sess1&url=https://example.com/audio.mp3")
    assert res_media.status_code == 401


def test_crm_set_session_preference_rejects_unowned_session(client, db):
    """Garante que definir preferred_session_id falha com 404 se a sessão não existir na WhatsappAccount do tenant."""
    user = User(
        email="pref_tester@tenant.com",
        hashed_password="pw",
        tenant_id="tenant_pref_test",
        role="custom",
        can_manage_crm=True
    )
    db.add(user)
    db.commit()

    token = create_access_token({
        "sub": user.email,
        "user_id": str(user.id),
        "role": user.role,
        "permissions": "read,write",
        "tenant_id": user.tenant_id
    })
    headers = {"Authorization": f"Bearer {token}"}

    res = client.put(
        f"{settings.API_V1_STR}/crm/session-preference",
        json={"session_id": "unregistered_session_xyz"},
        headers=headers
    )
    assert res.status_code == 404
    assert "não encontrada" in res.json()["detail"]


def test_resolve_owned_whatsapp_session_same_name_different_tenants(db):
    """
    Garante que dois tenants diferentes podem ter uma sessão com o mesmo session_id ('principal'),
    e cada usuário resolve sua própria sessão sem colisão ou erro 403.
    Garante também que se User C (tenant_c) tentar acessar 'principal', recebe 403 (pois pertence a outro tenant),
    e se tentar acessar 'inexistente', recebe 404.
    """
    from app.services.whatsapp_service import resolve_owned_whatsapp_session

    user_a = User(email="user_a_sess@tenant-a.com", hashed_password="pw", tenant_id="tenant_a_wa", role="custom")
    user_b = User(email="user_b_sess@tenant-b.com", hashed_password="pw", tenant_id="tenant_b_wa", role="custom")
    user_c = User(email="user_c_sess@tenant-c.com", hashed_password="pw", tenant_id="tenant_c_wa", role="custom")
    db.add_all([user_a, user_b, user_c])
    db.commit()

    acc_a = WhatsappAccount(user_id=user_a.id, tenant_id="tenant_a_wa", session_id="principal")
    acc_b = WhatsappAccount(user_id=user_b.id, tenant_id="tenant_b_wa", session_id="principal")
    db.add_all([acc_a, acc_b])
    db.commit()

    # User A resolves "principal" -> ok
    assert resolve_owned_whatsapp_session(user_a, "principal", db) == "principal"

    # User B resolves "principal" -> ok
    assert resolve_owned_whatsapp_session(user_b, "principal", db) == "principal"

    # User C tries to resolve "principal" -> 403 Forbidden (cross-tenant)
    with pytest.raises(HTTPException) as exc_403:
        resolve_owned_whatsapp_session(user_c, "principal", db)
    assert exc_403.value.status_code == 403

    # User C tries to resolve unknown session -> 404 Not Found
    with pytest.raises(HTTPException) as exc_404:
        resolve_owned_whatsapp_session(user_c, "sessao_inexistente", db)
    assert exc_404.value.status_code == 404


