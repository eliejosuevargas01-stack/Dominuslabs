import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_access_token
from app.core.config import settings
from app.models.product import Product
from app.models.product_media import ProductMedia


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
        "tenant_id": user.tenant_id,
    })
    return {"Authorization": f"Bearer {token}"}


def create_product(db, tenant_id: str | None = None) -> Product:
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id or settings.ADMIN_TENANT_ID,
        codigo_slug=f"produto-{uuid.uuid4()}",
        nome="Produto de teste",
        preco=10.0,
        disponivel=True,
        estoque=1,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_upload_product_media_image(
    client: TestClient,
    db,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    product = create_product(db)

    response = client.post(
        f"{settings.API_V1_STR}/product-media/",
        files={"file": ("product.png", b"fake image data", "image/png")},
        data={"product_id": str(product.id), "tenant_id": "untrusted-tenant"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == str(product.id)
    assert data["tenant_id"] == settings.ADMIN_TENANT_ID
    assert data["media_type"] == "image"
    assert data["media_url"].startswith("/uploads/products/prod_")

    media = db.query(ProductMedia).filter(ProductMedia.product_id == product.id).one()
    db.refresh(product)
    assert media.media_url == data["media_url"]
    assert product.imagem_url == data["media_url"]
    assert (tmp_path / "products" / data["media_url"].rsplit("/", 1)[-1]).is_file()


def test_upload_product_media_video(
    client: TestClient,
    db,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    product = create_product(db)

    response = client.post(
        f"{settings.API_V1_STR}/product-media/",
        files={"file": ("product.mp4", b"fake video data", "video/mp4")},
        data={"product_id": str(product.id)},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["media_type"] == "video"


def test_upload_product_media_invalid_type(
    client: TestClient,
    db,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    product = create_product(db)

    response = client.post(
        f"{settings.API_V1_STR}/product-media/",
        files={"file": ("product.pdf", b"fake pdf data", "application/pdf")},
        data={"product_id": str(product.id)},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "supported" in response.json()["detail"].lower()


def test_upload_product_media_rejects_temporary_product_id(
    client: TestClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    response = client.post(
        f"{settings.API_V1_STR}/product-media/",
        files={"file": ("product.png", b"fake image data", "image/png")},
        data={"product_id": "item-123456"},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert not (tmp_path / "products").exists()


def test_upload_product_media_requires_existing_product(
    client: TestClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    response = client.post(
        f"{settings.API_V1_STR}/product-media/",
        files={"file": ("product.png", b"fake image data", "image/png")},
        data={"product_id": str(uuid.uuid4())},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Produto não encontrado"
    assert not (tmp_path / "products").exists()


def test_upload_product_media_rejects_cross_tenant_product(
    client: TestClient,
    db,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    foreign_product = create_product(db, tenant_id="foreign-tenant")

    response = client.post(
        f"{settings.API_V1_STR}/product-media/",
        files={"file": ("product.png", b"fake image data", "image/png")},
        data={"product_id": str(foreign_product.id), "tenant_id": "foreign-tenant"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert not (tmp_path / "products").exists()
