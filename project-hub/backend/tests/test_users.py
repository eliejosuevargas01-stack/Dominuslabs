import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.core.database import get_db
from app.core.auth import check_admin_role, get_current_user
from app.models.user import User

client = TestClient(app)

def mock_check_admin_role():
    return "admin@dominuslabs.online"

def mock_get_current_user():
    return "admin@dominuslabs.online"

app.dependency_overrides[check_admin_role] = mock_check_admin_role
app.dependency_overrides[get_current_user] = mock_get_current_user

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@patch("app.api.endpoints.users.user_repo.get_all")
def test_read_users(mock_get_all, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_admin_role] = mock_check_admin_role
    now = datetime.now()
    mock_get_all.return_value = [{"id": 1, "email": "test@dominuslabs.online", "role": "admin", "permissions": "read", "tenant_id": "t1", "whatsapp_token": "w1", "created_at": now}]

    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    assert response.json()[0]["id"] == 1
    mock_get_all.assert_called_once()


@patch("app.api.endpoints.users.user_repo.get_by_email")
@patch("app.api.endpoints.users.user_repo.create")
def test_create_user(mock_create, mock_get_by_email, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_admin_role] = mock_check_admin_role
    mock_get_by_email.return_value = None
    now = datetime.now()
    mock_create.return_value = {"id": 2, "email": "new@dominuslabs.online", "role": "custom", "permissions": "read", "tenant_id": "t2", "whatsapp_token": "w2", "created_at": now}

    payload = {
        "email": "new@dominuslabs.online",
        "password": "password123",
        "role": "custom"
    }
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 200
    assert response.json()["email"] == "new@dominuslabs.online"


@patch("app.api.endpoints.users.user_repo.get")
@patch("app.api.endpoints.users.user_repo.remove")
def test_delete_user(mock_remove, mock_get, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_admin_role] = mock_check_admin_role
    user_mock = MagicMock()
    user_mock.email = "other@dominuslabs.online"
    mock_get.return_value = user_mock

    response = client.delete("/api/v1/users/2")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Usuário excluído com sucesso."}
    mock_remove.assert_called_once()

@patch("app.api.endpoints.users.user_repo.get")
def test_delete_user_self_fail(mock_get, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_admin_role] = mock_check_admin_role
    user_mock = MagicMock()
    user_mock.email = "admin@dominuslabs.online"
    mock_get.return_value = user_mock

    response = client.delete("/api/v1/users/1")
    assert response.status_code == 400
    assert response.json()["detail"] == "Você não pode excluir o seu próprio usuário."


@patch("app.api.endpoints.users.user_repo.get_by_email")
def test_gdpr_anonymize(mock_get_by_email, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    user_mock = MagicMock()
    user_mock.email = "admin@dominuslabs.online"
    mock_get_by_email.return_value = user_mock

    response = client.post("/api/v1/users/gdpr/anonymize")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    assert "anonymized_" in user_mock.email
    assert user_mock.role == "anonymized"
    mock_db.commit.assert_called_once()

@patch("app.api.endpoints.users.user_repo.get")
@patch("app.api.endpoints.users.user_repo.get_by_email")
@patch("app.api.endpoints.users.user_repo.update")
def test_update_user(mock_update, mock_get_by_email, mock_get, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_admin_role] = mock_check_admin_role

    user_mock = MagicMock()
    user_mock.email = "old@dominuslabs.online"
    mock_get.return_value = user_mock
    mock_get_by_email.return_value = None

    now = datetime.now()
    mock_update.return_value = {"id": 2, "email": "updated@dominuslabs.online", "role": "admin", "permissions": "read,write", "tenant_id": "t2", "whatsapp_token": "w2", "created_at": now}

    payload = {
        "email": "updated@dominuslabs.online",
        "role": "admin"
    }
    response = client.put("/api/v1/users/2", json=payload)
    assert response.status_code == 200
    assert response.json()["email"] == "updated@dominuslabs.online"
