import pytest
from unittest.mock import patch, mock_open, MagicMock
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.auth import create_access_token, check_crm_permission
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
        "tenant_id": user.tenant_id
    })
    return {"Authorization": f"Bearer {token}"}

def override_get_db(mock_db_session):
    def _override():
        yield mock_db_session
    return _override

@patch("app.api.endpoints.product_media.os.makedirs")
@patch("app.api.endpoints.product_media.shutil.copyfileobj")
def test_upload_product_media_image(mock_copy, mock_makedirs, client: TestClient, auth_headers: dict):
    # Mock database session
    mock_db = MagicMock()
    # When db.refresh is called, it assigns id = 1
    def mock_refresh(obj):
        obj.id = 1
    mock_db.refresh.side_effect = mock_refresh

    from app.main import app
    from app.core.database import get_db
    app.dependency_overrides[get_db] = override_get_db(mock_db)
    app.dependency_overrides[check_crm_permission] = lambda: True

    file_content = b"fake image data"
    files = {"file": ("product.png", file_content, "image/png")}
    data = {"product_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", "tenant_id": "test_tenant"}

    with patch("builtins.open", mock_open()):
        response = client.post(f"{settings.API_V1_STR}/product-media/", files=files, data=data, headers=auth_headers)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["product_id"] == "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    assert res_data["media_type"] == "image"
    assert "media_url" in res_data

    mock_makedirs.assert_called_once()
    mock_copy.assert_called_once()
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@patch("app.api.endpoints.product_media.os.makedirs")
@patch("app.api.endpoints.product_media.shutil.copyfileobj")
def test_upload_product_media_video(mock_copy, mock_makedirs, client: TestClient, auth_headers: dict):
    mock_db = MagicMock()
    def mock_refresh(obj):
        obj.id = 2
    mock_db.refresh.side_effect = mock_refresh

    from app.main import app
    from app.core.database import get_db
    app.dependency_overrides[get_db] = override_get_db(mock_db)
    app.dependency_overrides[check_crm_permission] = lambda: True

    file_content = b"fake video data"
    files = {"file": ("product.mp4", file_content, "video/mp4")}
    data = {"product_id": "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22", "tenant_id": "test_tenant"}

    with patch("builtins.open", mock_open()):
        response = client.post(f"{settings.API_V1_STR}/product-media/", files=files, data=data, headers=auth_headers)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["product_id"] == "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"
    assert res_data["media_type"] == "video"

    mock_makedirs.assert_called_once()
    mock_copy.assert_called_once()
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

def test_upload_product_media_invalid_type(client: TestClient, auth_headers: dict):
    file_content = b"fake pdf data"
    files = {"file": ("product.pdf", file_content, "application/pdf")}
    data = {"product_id": "c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33", "tenant_id": "test_tenant"}

    response = client.post(f"{settings.API_V1_STR}/product-media/", files=files, data=data, headers=auth_headers)

    assert response.status_code == 400
    assert "supported" in response.json()["detail"].lower()
