import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_auth(mocker):
    # Mocking the dependency directly on the router or through override
    # Since FastAPI uses Depends, we can override app.dependency_overrides
    from app.core.auth import (
        check_crm_permission,
        check_product_read_permission,
        check_product_create_permission,
        check_product_update_permission,
        check_product_delete_permission,
    )
    from app.api.endpoints.products import get_tenant_id_for_user
    
    async def override_permission():
        return "test@example.com"
        
    app.dependency_overrides[check_crm_permission] = override_permission
    app.dependency_overrides[check_product_read_permission] = override_permission
    app.dependency_overrides[check_product_create_permission] = override_permission
    app.dependency_overrides[check_product_update_permission] = override_permission
    app.dependency_overrides[check_product_delete_permission] = override_permission
    
    # Mock get_tenant_id_for_user and db queries
    mocker.patch("app.api.endpoints.products.get_tenant_id_for_user", return_value="tenant-123")
    
    # Mock DB Session
    mock_db = mocker.MagicMock()
    mock_user = mocker.MagicMock()
    mock_db.query().filter().first.return_value = mock_user
    
    yield mock_db
    app.dependency_overrides = {}

def test_get_products(mock_auth, mocker):
    mock_product = mocker.MagicMock()
    mock_product.id = "prod-1"
    mock_product.tenant_id = "tenant-123"
    mock_product.nome = "Test Product"
    mock_product.categoria = "Test Category"
    mock_product.preco = 10.0
    mock_product.descricao = "Test Description"
    mock_product.disponivel = True
    mock_product.imagem_url = "http://example.com/img.png"
    mock_product.estoque = 5
    from datetime import datetime, timezone, timezone, timezone
    mock_product.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    mock_product.descricao = "Test Description"
    mock_product.disponivel = True
    mock_product.imagem_url = "http://example.com/img.png"
    mock_product.estoque = 5
    mock_product.created_at = "2023-01-01T00:00:00Z"
    
    mock_auth.query().filter().all.return_value = [mock_product]
    
    # We must patch get_db as well
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_auth
    
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Product"
    assert data[0]["price"] == 10.0
    
def test_create_product(mock_auth, mocker):
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_auth
    
    # We need to ensure the mocked product returned by add/refresh has created_at
    def mock_refresh(obj):
        from datetime import datetime, timezone
        obj.id = "new-uuid"
        obj.created_at = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_auth.refresh.side_effect = mock_refresh

    response = client.post("/api/v1/products", json={
        "name": "New Product",
        "category": "Cat",
        "price": 20.5,
        "description": "Desc",
        "available": True,
        "image_url": "http://img.com",
        "stock": 10
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Product"
    assert mock_auth.add.called
    assert mock_auth.commit.called
    assert mock_auth.refresh.called

def test_update_product(mock_auth, mocker):
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_auth
    
    # Need to return a product when queried by ID
    mock_product = mocker.MagicMock()
    mock_product.id = "prod-1"
    mock_product.tenant_id = "tenant-123"
    mock_product.nome = "Test Product"
    mock_product.categoria = "Test Category"
    mock_product.preco = 10.0
    mock_product.descricao = "Test Description"
    mock_product.disponivel = True
    mock_product.imagem_url = "http://example.com/img.png"
    mock_product.estoque = 5
    from datetime import datetime, timezone
    mock_product.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # query().filter().first() is called twice (user, then product)
    # We can handle this by side_effect
    mock_auth.query().filter().first.side_effect = [mocker.MagicMock(), mock_product]
    
    response = client.put("/api/v1/products/prod-1", json={
        "name": "Updated Product",
        "price": 15.0
    })
    
    assert response.status_code == 200
    data = response.json()
    assert mock_product.nome == "Updated Product"
    assert mock_product.preco == 15.0
    
def test_update_product_not_found(mock_auth, mocker):
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_auth
    
    # Return None for product
    mock_auth.query().filter().first.side_effect = [mocker.MagicMock(), None]
    
    response = client.put("/api/v1/products/prod-1", json={
        "name": "Updated Product"
    })
    assert response.status_code == 404

def test_delete_product(mock_auth, mocker):
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_auth
    
    mock_product = mocker.MagicMock()
    mock_auth.query().filter().first.side_effect = [mocker.MagicMock(), mock_product]
    
    response = client.delete("/api/v1/products/prod-1")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert mock_auth.delete.called
    assert mock_auth.commit.called

def test_delete_product_not_found(mock_auth, mocker):
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_auth
    
    mock_auth.query().filter().first.side_effect = [mocker.MagicMock(), None]
    
    response = client.delete("/api/v1/products/prod-1")
    assert response.status_code == 404
