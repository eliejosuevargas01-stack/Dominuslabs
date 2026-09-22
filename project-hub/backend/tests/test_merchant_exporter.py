"""Tests for the Open Delivery merchant exporter and GET /merchant endpoint."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.models.company_setting import CompanySetting
from app.models.product import Product
from app.models.tenant_platform_integration import TenantPlatformIntegration
from app.api.endpoints.open_delivery import router
from app.services.merchant_exporter import export_merchant
from app.main import app

# --------------------------------------------------------------------------- #
# In-memory SQLite test database (mirrors conftest patterns).                  #
# --------------------------------------------------------------------------- #
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
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
def db(test_db):
    """Alias used by tests that just need a session."""
    return test_db


@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Helper builders.                                                              #
# --------------------------------------------------------------------------- #
def _make_integration(test_db, merchant_id="m_123", platform="open_delivery", tenant_id="tenant_a", is_active=True):
    integration = TenantPlatformIntegration(
        tenant_id=tenant_id,
        platform=platform,
        merchant_id=merchant_id,
        base_url="https://example.com",
        credentials_enc="{}",
        is_active=is_active,
    )
    test_db.add(integration)
    test_db.commit()
    test_db.refresh(integration)
    return integration


def _make_company(test_db, tenant_id="tenant_a", **overrides):
    company = CompanySetting(
        tenant_id=tenant_id,
        company_name="Empresa Teste",
        cnpj_cpf="11222333000144",
        address="Rua das Flores",
        address_number="123",
        address_neighborhood="Centro",
        address_city="Sao Paulo",
        address_state="SP",
        address_zip="01234-567",
        **overrides,
    )
    test_db.add(company)
    test_db.commit()
    test_db.refresh(company)
    return company


def _make_product(test_db, tenant_id="tenant_a", codigo_slug="p1", nome="Produto 1",
                  categoria="Bebidas", preco=10.0, disponivel=True, imagem_url="http://img/p1.png"):
    product = Product(
        tenant_id=tenant_id,
        codigo_slug=codigo_slug,
        nome=nome,
        categoria=categoria,
        preco=preco,
        disponivel=disponivel,
        imagem_url=imagem_url,
        estoque=0,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)
    return product


# --------------------------------------------------------------------------- #
# Service-level tests.                                                          #
# --------------------------------------------------------------------------- #
def test_export_merchant_completo(test_db):
    """CompanySetting + multiple products across categories -> correct schema."""
    _make_company(test_db, tenant_id="tenant_a")
    _make_product(test_db, tenant_id="tenant_a", codigo_slug="p1", nome="Coca-Cola", categoria="Bebidas", preco=5.50)
    _make_product(test_db, tenant_id="tenant_a", codigo_slug="p2", nome="Pepsi", categoria="Bebidas", preco=4.50)
    _make_product(test_db, tenant_id="tenant_a", codigo_slug="p3", nome="Pizza", categoria="Comida", preco=30.0, disponivel=False)
    _make_product(test_db, tenant_id="tenant_a", codigo_slug="p4", nome="Salgado", categoria=None, preco=8.0)
    _make_integration(test_db, tenant_id="tenant_a", merchant_id="m_123")

    result = export_merchant("tenant_a", test_db)

    # Identity + document + address from CompanySetting.
    assert result["id"] == "m_123"
    assert result["name"] == "Empresa Teste"
    assert result["document"] == {"number": "11222333000144", "type": "CNPJ"}
    assert result["address"] == {
        "streetName": "Rua das Flores",
        "streetNumber": "123",
        "neighborhood": "Centro",
        "city": "Sao Paulo",
        "state": "SP",
        "postalCode": "01234-567",
    }

    # Categories: Bebidas -> cat-0, Comida -> cat-1, Outros -> cat-2 (order of first appearance).
    assert result["categories"] == [
        {"id": "cat-0", "name": "Bebidas", "sequence": 0},
        {"id": "cat-1", "name": "Comida", "sequence": 1},
        {"id": "cat-2", "name": "Outros", "sequence": 2},
    ]

    # Items.
    items = result["items"]
    assert len(items) == 4
    by_slug = {it["id"]: it for it in items}

    assert by_slug["p1"]["name"] == "Coca-Cola"
    assert by_slug["p1"]["price"] == {"value": 5.50, "currency": "BRL"}
    assert by_slug["p1"]["status"] == "AVAILABLE"
    assert by_slug["p1"]["categoryId"] == "cat-0"
    assert by_slug["p1"]["externalCode"] == "p1"
    assert by_slug["p1"]["imagePath"] == "http://img/p1.png"

    assert by_slug["p3"]["status"] == "UNAVAILABLE"
    assert by_slug["p3"]["categoryId"] == "cat-1"


def test_export_merchant_sem_company_setting(test_db):
    """No CompanySetting -> minimal schema with id=tenant_id, items=[]"""
    _make_integration(test_db, tenant_id="tenant_b", merchant_id="m_999")
    _make_product(test_db, tenant_id="tenant_b", categoria="X", codigo_slug="px1")

    result = export_merchant("tenant_b", test_db)

    assert result["id"] == "m_999"  # merchant_id from integration
    assert result["name"] == "tenant_b"  # fallback to tenant_id
    assert result["document"] == {"number": None, "type": "CNPJ"}
    assert result["address"] == {
        "streetName": None,
        "streetNumber": None,
        "neighborhood": None,
        "city": None,
        "state": None,
        "postalCode": None,
    }
    assert result["categories"] == []
    assert result["items"] == []


def test_export_merchant_sem_produtos(test_db):
    """CompanySetting but no products -> empty items and categories."""
    _make_company(test_db, tenant_id="tenant_c")
    _make_integration(test_db, tenant_id="tenant_c", merchant_id="m_456")

    result = export_merchant("tenant_c", test_db)

    assert result["id"] == "m_456"
    assert result["categories"] == []
    assert result["items"] == []


def test_export_merchant_isolamento_tenant(test_db):
    """Products of another tenant must never appear."""
    _make_company(test_db, tenant_id="tenant_a")
    _make_integration(test_db, tenant_id="tenant_a", merchant_id="m_123")
    _make_product(test_db, tenant_id="tenant_a", codigo_slug="a1", nome="A1", categoria="Doces")
    _make_product(test_db, tenant_id="tenant_b", codigo_slug="b1", nome="B1", categoria="Salgados")

    result = export_merchant("tenant_a", test_db)

    slugs = {it["id"] for it in result["items"]}
    assert slugs == {"a1"}  # b1 (other tenant) excluded
    assert result["categories"] == [{"id": "cat-0", "name": "Doces", "sequence": 0}]


# --------------------------------------------------------------------------- #
# Endpoint tests.                                                             #
# --------------------------------------------------------------------------- #
def test_endpoint_merchant_ok(client, test_db):
    """GET /merchant returns 200 with a valid schema."""
    _make_company(test_db, tenant_id="tenant_a")
    _make_integration(test_db, tenant_id="tenant_a", merchant_id="m_123", platform="open_delivery")
    _make_product(test_db, tenant_id="tenant_a", codigo_slug="p1", nome="Coca", categoria="Bebidas", preco=5.5)

    response = client.get(
        "/api/v1/od/open_delivery/merchant",
        headers={
            "Authorization": "Bearer token",
            "X-Merchant-Id": "m_123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "m_123"
    assert body["name"] == "Empresa Teste"
    assert body["document"]["type"] == "CNPJ"
    assert body["document"]["number"] == "11222333000144"
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == "p1"
    assert body["items"][0]["categoryId"] == "cat-0"
    assert body["categories"] == [{"id": "cat-0", "name": "Bebidas", "sequence": 0}]


def test_endpoint_merchant_sem_token(client, test_db):
    """GET /merchant without Authorization returns 401."""
    response = client.get(
        "/api/v1/od/open_delivery/merchant",
        headers={"X-Merchant-Id": "m_123"},
    )
    assert response.status_code == 401


def test_endpoint_merchant_merchant_desconhecido(client, test_db):
    """GET /merchant with unknown merchant_id returns 404."""
    response = client.get(
        "/api/v1/od/open_delivery/merchant",
        headers={"Authorization": "Bearer token", "X-Merchant-Id": "unknown_m"},
    )
    assert response.status_code == 404
