import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import json

from app.main import app
from app.core.database import get_db
from app.models.user import User
from app.models.tenant_platform_integration import TenantPlatformIntegration
from app.core.security import get_password_hash

client = TestClient(app)


@pytest.fixture
def mock_db():
    mock_session = MagicMock()
    yield mock_session


def _setup_user_mock(mock_db, user_mock):
    """Setup db mock for user query and set dependency override."""
    mock_user_query = MagicMock()
    mock_user_filter = MagicMock()
    mock_user_first = MagicMock(return_value=user_mock)
    mock_user_filter.first = mock_user_first
    mock_user_query.filter.return_value = mock_user_filter
    mock_db.query.side_effect = lambda model: mock_user_query if model == User else MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db


def _login_and_get_token(user_mock_email, user_mock_password):
    """Login and return access token."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": user_mock_email, "password": user_mock_password}
    )
    return login_response.json()["access_token"]


@pytest.fixture
def auth_token(mock_db):
    """Login a mock user and return the JWT token + user info."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        _setup_user_mock(mock_db, user_mock)
        token = _login_and_get_token("test@dominuslabs.online", "test")
        yield token
        app.dependency_overrides.clear()


def test_list_integrations_vazio(mock_db):
    """Testa listagem de integrações quando não há nenhuma."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        # Setup db mock for user query
        mock_user_query = MagicMock()
        mock_user_filter = MagicMock()
        mock_user_first = MagicMock(return_value=user_mock)
        mock_user_filter.first = mock_user_first
        mock_user_query.filter.return_value = mock_user_filter

        # Setup db mock for integrations query (empty list)
        mock_int_query = MagicMock()
        mock_int_filter = MagicMock()
        mock_int_all = MagicMock(return_value=[])
        mock_int_filter.all = mock_int_all
        mock_int_query.filter.return_value = mock_int_filter

        def query_side_effect(model):
            if model == User:
                return mock_user_query
            elif model == TenantPlatformIntegration:
                return mock_int_query
            return MagicMock()
        mock_db.query.side_effect = query_side_effect

        app.dependency_overrides[get_db] = lambda: mock_db

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@dominuslabs.online", "password": "test"}
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/integrations",
            headers={"Authorization": f"Bearer {token}"}
        )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == []


def test_create_integration_valida(mock_db):
    """Testa criação de integração válida."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        # Setup db mock for user query
        mock_user_query = MagicMock()
        mock_user_filter = MagicMock()
        mock_user_first = MagicMock(return_value=user_mock)
        mock_user_filter.first = mock_user_first
        mock_user_query.filter.return_value = mock_user_filter

        # Setup db mock for duplicate check (no existing)
        mock_dup_query = MagicMock()
        mock_dup_filter = MagicMock()
        mock_dup_first = MagicMock(return_value=None)
        mock_dup_filter.first = mock_dup_first
        mock_dup_query.filter.return_value = mock_dup_filter

        # Setup db mock for add/commit/refresh
        created_integration = TenantPlatformIntegration(
            id="new-integration-id",
            tenant_id="tenant_1",
            platform="pedidos10",
            display_name="Pedidos10 - Loja Centro",
            credentials_enc="encrypted",
            merchant_id="LOJA001",
            base_url="https://api.pedidos10.com.br",
            auth_url="https://auth.pedidos10.com.br",
            is_active=True,
            onboarding_status="active",
            store_code="LOJA001",
            last_sync_at=None,
            last_error=None
        )

        def query_side_effect(model):
            if model == User:
                return mock_user_query
            elif model == TenantPlatformIntegration:
                return mock_dup_query
            return MagicMock()
        mock_db.query.side_effect = query_side_effect
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock(side_effect=lambda x: x)
        mock_db.add = MagicMock()

        app.dependency_overrides[get_db] = lambda: mock_db

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@dominuslabs.online", "password": "test"}
        )
        token = login_response.json()["access_token"]

        # Create integration
        response = client.post(
            "/api/v1/integrations",
            json={
                "platform": "pedidos10",
                "store_code": "LOJA001",
                "display_name": "Pedidos10 - Loja Centro"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "pedidos10"
        assert data["store_code"] == "LOJA001"
        assert data["display_name"] == "Pedidos10 - Loja Centro"
        assert data["is_active"] == True
        assert data["onboarding_status"] == "active"
        assert "id" in data


def test_create_integration_platform_invalida(mock_db):
    """Testa criação com plataforma inválida."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        # Setup db mock for user query
        mock_user_query = MagicMock()
        mock_user_filter = MagicMock()
        mock_user_first = MagicMock(return_value=user_mock)
        mock_user_filter.first = mock_user_first
        mock_user_query.filter.return_value = mock_user_filter
        mock_db.query.side_effect = lambda model: mock_user_query if model == User else MagicMock()

        app.dependency_overrides[get_db] = lambda: mock_db

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@dominuslabs.online", "password": "test"}
        )
        token = login_response.json()["access_token"]

        # Create integration with invalid platform
        response = client.post(
            "/api/v1/integrations",
            json={
                "platform": "platform_invalido",
                "store_code": "LOJA001"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        app.dependency_overrides.clear()

        assert response.status_code == 400
        assert "Plataforma não suportada" in response.json()["detail"]


def test_create_integration_duplicada(mock_db):
    """Testa criação de integração duplicada para mesma plataforma."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        # Mock existing integration
        existing_integration = TenantPlatformIntegration(
            id="existing-id",
            tenant_id="tenant_1",
            platform="pedidos10",
            display_name="Existing",
            credentials_enc="encrypted",
            merchant_id="LOJA001",
            base_url="https://api.pedidos10.com.br",
            auth_url="https://auth.pedidos10.com.br",
            is_active=True,
            onboarding_status="active",
            store_code="LOJA001"
        )

        # Setup db mock for user query
        mock_user_query = MagicMock()
        mock_user_filter = MagicMock()
        mock_user_first = MagicMock(return_value=user_mock)
        mock_user_filter.first = mock_user_first
        mock_user_query.filter.return_value = mock_user_filter

        # Setup db mock for duplicate check (existing integration)
        mock_dup_query = MagicMock()
        mock_dup_filter = MagicMock()
        mock_dup_first = MagicMock(return_value=existing_integration)
        mock_dup_filter.first = mock_dup_first
        mock_dup_query.filter.return_value = mock_dup_filter

        def query_side_effect(model):
            if model == User:
                return mock_user_query
            elif model == TenantPlatformIntegration:
                return mock_dup_query
            return MagicMock()
        mock_db.query.side_effect = query_side_effect

        app.dependency_overrides[get_db] = lambda: mock_db

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@dominuslabs.online", "password": "test"}
        )
        token = login_response.json()["access_token"]

        # Try to create duplicate integration
        response = client.post(
            "/api/v1/integrations",
            json={
                "platform": "pedidos10",
                "store_code": "LOJA002"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        app.dependency_overrides.clear()

        assert response.status_code == 409
        assert "Já existe uma integração ativa" in response.json()["detail"]


def test_delete_integration(mock_db):
    """Testa delete de integração (soft delete)."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        # Mock integration to delete
        integration_to_delete = TenantPlatformIntegration(
            id="integration-id-123",
            tenant_id="tenant_1",
            platform="pedidos10",
            display_name="Test Integration",
            credentials_enc="encrypted-data",
            merchant_id="LOJA001",
            base_url="https://api.pedidos10.com.br",
            auth_url="https://auth.pedidos10.com.br",
            is_active=True,
            onboarding_status="active",
            store_code="LOJA001",
            last_sync_at=None,
            last_error=None
        )

        # Setup db mock for user query
        mock_user_query = MagicMock()
        mock_user_filter = MagicMock()
        mock_user_first = MagicMock(return_value=user_mock)
        mock_user_filter.first = mock_user_first
        mock_user_query.filter.return_value = mock_user_filter

        # Setup db mock for integration query
        mock_int_query = MagicMock()
        mock_int_filter = MagicMock()
        mock_int_first = MagicMock(return_value=integration_to_delete)
        mock_int_filter.first = mock_int_first
        mock_int_query.filter.return_value = mock_int_filter

        def query_side_effect(model):
            if model == User:
                return mock_user_query
            elif model == TenantPlatformIntegration:
                return mock_int_query
            return MagicMock()
        mock_db.query.side_effect = query_side_effect
        mock_db.commit = MagicMock()

        app.dependency_overrides[get_db] = lambda: mock_db

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@dominuslabs.online", "password": "test"}
        )
        token = login_response.json()["access_token"]

        # Delete integration
        response = client.delete(
            "/api/v1/integrations/integration-id-123",
            headers={"Authorization": f"Bearer {token}"}
        )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["ok"] == True

        # Verify soft delete happened (is_active=False, credentials_enc='')
        assert integration_to_delete.is_active == False
        assert integration_to_delete.credentials_enc == ""


def test_patch_integration_toggle(mock_db):
    """Testa patch para ativar/desativar integração."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        # Mock integration
        integration = TenantPlatformIntegration(
            id="integration-id-456",
            tenant_id="tenant_1",
            platform="ifood",
            display_name="iFood Integration",
            credentials_enc="encrypted-data",
            merchant_id="LOJA002",
            base_url="https://merchant-api.ifood.com.br",
            auth_url="https://merchant-api.ifood.com.br/authentication",
            is_active=True,
            onboarding_status="active",
            store_code="LOJA002",
            last_sync_at=None,
            last_error=None
        )

        # Setup db mock for user query
        mock_user_query = MagicMock()
        mock_user_filter = MagicMock()
        mock_user_first = MagicMock(return_value=user_mock)
        mock_user_filter.first = mock_user_first
        mock_user_query.filter.return_value = mock_user_filter

        # Setup db mock for integration query
        mock_int_query = MagicMock()
        mock_int_filter = MagicMock()
        mock_int_first = MagicMock(return_value=integration)
        mock_int_filter.first = mock_int_first
        mock_int_query.filter.return_value = mock_int_filter

        def query_side_effect(model):
            if model == User:
                return mock_user_query
            elif model == TenantPlatformIntegration:
                return mock_int_query
            return MagicMock()
        mock_db.query.side_effect = query_side_effect
        mock_db.commit = MagicMock()

        app.dependency_overrides[get_db] = lambda: mock_db

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@dominuslabs.online", "password": "test"}
        )
        token = login_response.json()["access_token"]

        # Patch to deactivate
        response = client.patch(
            "/api/v1/integrations/integration-id-456",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"}
        )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "integration-id-456"
        assert data["is_active"] == False

        # Verify integration was updated
        assert integration.is_active == False


def test_nao_acessa_integracao_de_outro_tenant(mock_db):
    """Testa que não é possível acessar integração de outro tenant."""
    with patch("app.api.endpoints.auth.get_db", return_value=mock_db):
        user_mock = User(
            id=1,
            email="test@dominuslabs.online",
            hashed_password=get_password_hash("test"),
            tenant_id="tenant_1",
            role="custom"
        )

        # Setup db mock for user query
        mock_user_query = MagicMock()
        mock_user_filter = MagicMock()
        mock_user_first = MagicMock(return_value=user_mock)
        mock_user_filter.first = mock_user_first
        mock_user_query.filter.return_value = mock_user_filter

        # Setup db mock for integration query (should return None due to tenant mismatch)
        mock_int_query = MagicMock()
        mock_int_filter = MagicMock()
        mock_int_first = MagicMock(return_value=None)  # Not found due to tenant_id filter
        mock_int_filter.first = mock_int_first
        mock_int_query.filter.return_value = mock_int_filter

        def query_side_effect(model):
            if model == User:
                return mock_user_query
            elif model == TenantPlatformIntegration:
                return mock_int_query
            return MagicMock()
        mock_db.query.side_effect = query_side_effect

        app.dependency_overrides[get_db] = lambda: mock_db

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@dominuslabs.online", "password": "test"}
        )
        token = login_response.json()["access_token"]

        # Try to access integration from other tenant
        response = client.delete(
            "/api/v1/integrations/integration-id-789",
            headers={"Authorization": f"Bearer {token}"}
        )

        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "Integração não encontrada" in response.json()["detail"]