"""Tests for Open Delivery inbound webhook adapter."""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.tenant_platform_integration import TenantPlatformIntegration
from app.models.order_manager import OrderManagerOrder, OrderManagerOrderItem
from app.services.open_delivery_adapter import convert_order_inbound


# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database with all tables."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client(test_db):
    """Create a TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_integration(test_db):
    """Create a sample TenantPlatformIntegration for testing."""
    integration = TenantPlatformIntegration(
        tenant_id="test_tenant",
        platform="open_delivery",
        merchant_id="merchant_123",
        base_url="https://example.com",
        credentials_enc="{}",
        is_active=True,
    )
    test_db.add(integration)
    test_db.commit()
    test_db.refresh(integration)
    return integration


def test_convert_order_inbound():
    """Test the Open Delivery adapter conversion function."""
    od_payload = {
        "merchantId": "merchant_123",
        "order": {
            "id": "order_456",
            "customer": {
                "name": "John Doe"
            },
            "delivery": {
                "street": "Rua das Flores",
                "number": "123",
                "complement": "Apt 456",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "postalCode": "01234-567"
            },
            "total": {
                "orderAmount": "123.45"
            },
            "merchant": {
                "id": "merchant_123"
            }
        },
        "items": [
            {
                "externalCode": "PROD_001",
                "name": "Produto Teste 1",
                "quantity": 2,
                "unitPrice": "10.00",
                "totalPrice": "20.00",
                "observations": "Sem cebola"
            },
            {
                "externalCode": "PROD_002",
                "name": "Produto Teste 2",
                "quantity": 1,
                "unitPrice": "50.00",
                "totalPrice": "50.00"
            }
        ]
    }
    
    result = convert_order_inbound(od_payload, "test_tenant", "open_delivery")
    
    # Check order level fields
    assert result["external_order_id"] == "order_456"
    assert result["source_platform"] == "open_delivery"
    assert result["tenant_id"] == "test_tenant"
    assert result["pedido_id"] == "order_456"
    assert result["cliente_id"] == "open_delivery:merchant_123"
    assert result["client_jid"] is None
    assert result["content_jid"] is None
    assert result["customer_name"] == "John Doe"
    assert result["address"] == "Rua das Flores, 123, Apt 456, Centro, São Paulo, SP, 01234-567"
    assert result["total"] == Decimal("123.45")
    assert result["status"] == "pending"
    
    # Check items
    assert len(result["items"]) == 2
    
    item1 = result["items"][0]
    assert item1["external_item_id"] == "PROD_001"
    assert item1["tenant_id"] == "test_tenant"
    assert item1["pedido_id"] == "order_456"
    assert item1["codigo"] == "PROD_001"
    assert item1["nome"] == "Produto Teste 1"
    assert item1["quantidade"] == 2
    assert item1["preco_unitario"] == Decimal("10.00")
    assert item1["subtotal"] == Decimal("20.00")
    assert item1["observacoes"] == "Sem cebola"
    
    item2 = result["items"][1]
    assert item2["external_item_id"] == "PROD_002"
    assert item2["nome"] == "Produto Teste 2"
    assert item2["quantidade"] == 1
    assert item2["preco_unitario"] == Decimal("50.00")
    assert item2["subtotal"] == Decimal("50.00")
    assert item2["observacoes"] is None


def test_orderupdate_cria_pedido(test_client, sample_integration, test_db):
    """Test that a valid payload creates an OrderManagerOrder in the DB."""
    payload = {
        "merchantId": "merchant_123",
        "order": {
            "id": "order_789",
            "customer": {
                "name": "Jane Doe"
            },
            "delivery": {
                "street": "Av. Paulista",
                "number": "1000",
                "city": "São Paulo",
                "state": "SP"
            },
            "total": {
                "orderAmount": "99.99"
            },
            "merchant": {
                "id": "merchant_123"
            }
        },
        "items": [
            {
                "externalCode": "ITEM_001",
                "name": "Test Item",
                "quantity": 3,
                "unitPrice": "10.00",
                "totalPrice": "30.00"
            }
        ]
    }
    
    # Mock the broadcast function to avoid background task issues
    with patch("app.api.endpoints.open_delivery.broadcast", new_callable=AsyncMock):
        response = test_client.post(
            "/api/v1/od/open_delivery/orderUpdate",
            json=payload,
            headers={"Authorization": "Bearer fake-token"}
        )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
    
    # Verify the order was created in the database
    order = test_db.query(OrderManagerOrder).filter(
        OrderManagerOrder.tenant_id == "test_tenant",
        OrderManagerOrder.external_order_id == "order_789"
    ).first()
    assert order is not None
    assert order.customer_name == "Jane Doe"
    assert order.address.startswith("Av. Paulista")
    assert order.total == Decimal("99.99")
    assert order.status == "pending"
    assert order.source_platform == "open_delivery"
    assert len(order.items) == 1
    
    item = order.items[0]
    assert item.external_item_id == "ITEM_001"
    assert item.codigo == "ITEM_001"
    assert item.nome == "Test Item"
    assert item.quantidade == 3
    assert item.preco_unitario == Decimal("10.00")
    assert item.subtotal == Decimal("30.00")


def test_orderupdate_sem_token(test_client):
    """Test that missing Authorization header returns 401."""
    payload = {
        "merchantId": "merchant_123",
        "order": {
            "id": "order_999",
            "customer": {"name": "Test"},
            "delivery": {},
            "total": {"orderAmount": "10.00"},
            "merchant": {"id": "merchant_123"}
        },
        "items": []
    }
    
    response = test_client.post(
        "/api/v1/od/open_delivery/orderUpdate",
        json=payload
        # No Authorization header
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_orderupdate_merchant_desconhecido(test_client):
    """Test that unknown merchant_id returns 404."""
    payload = {
        "merchantId": "unknown_merchant",
        "order": {
            "id": "order_888",
            "customer": {"name": "Test"},
            "delivery": {},
            "total": {"orderAmount": "10.00"},
            "merchant": {"id": "unknown_merchant"}
        },
        "items": []
    }
    
    response = test_client.post(
        "/api/v1/od/open_delivery/orderUpdate",
        json=payload,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_acknowledgment_ok(test_client, sample_integration):
    """Test that POST acknowledgment returns 200."""
    payload = {
        "merchantId": "merchant_123"
        # Minimal payload for acknowledgment
    }
    
    response = test_client.post(
        "/api/v1/od/open_delivery/events/acknowledgment",
        json=payload,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
