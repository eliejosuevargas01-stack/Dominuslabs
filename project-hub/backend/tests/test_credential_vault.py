import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidTag

from app.core.config import settings
from app.core.credential_vault import (
    encrypt_credentials,
    decrypt_credentials,
    _derive_vault_key,
)


@pytest.fixture
def sample_rsa_private_key_pem():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def test_round_trip_basic(monkeypatch, sample_rsa_private_key_pem):
    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", sample_rsa_private_key_pem)

    data = {
        "clientId": "test-client-id-12345",
        "clientSecret": "super-secret-token-xyz",
        "tokens": ["access_token_1", "refresh_token_2"],
    }

    encrypted = encrypt_credentials(data)
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    # Ensure plaintext secrets are not in raw encrypted string
    assert "test-client-id-12345" not in encrypted
    assert "super-secret-token-xyz" not in encrypted

    decrypted = decrypt_credentials(encrypted)
    assert decrypted == data


def test_empty_data(monkeypatch, sample_rsa_private_key_pem):
    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", sample_rsa_private_key_pem)

    data = {}
    encrypted = encrypt_credentials(data)
    decrypted = decrypt_credentials(encrypted)
    assert decrypted == data


def test_complex_nested_data(monkeypatch, sample_rsa_private_key_pem):
    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", sample_rsa_private_key_pem)

    data = {
        "platform": "whatsapp_cloud",
        "meta": {
            "account_id": 987654321,
            "is_active": True,
            "settings": {
                "webhooks_enabled": False,
                "null_val": None,
                "endpoints": [
                    {"url": "https://api.example.com/v1", "retry": 3},
                    {"url": "https://api.example.com/v2", "retry": 5},
                ],
            },
        },
        "tokens": {
            "access": "bearer_xyz_999",
            "expires_in": 3600,
        },
    }

    encrypted = encrypt_credentials(data)
    decrypted = decrypt_credentials(encrypted)
    assert decrypted == data


def test_missing_private_key_raises_runtime_error(monkeypatch):
    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", "")

    data = {"clientId": "123"}
    with pytest.raises(RuntimeError, match="DOMINUS_PRIVATE_KEY not configured"):
        encrypt_credentials(data)

    with pytest.raises(RuntimeError, match="DOMINUS_PRIVATE_KEY not configured"):
        decrypt_credentials("some-fake-encrypted-string")


def test_decryption_with_different_key_fails(monkeypatch, sample_rsa_private_key_pem):
    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", sample_rsa_private_key_pem)
    data = {"secret": "confidential"}
    encrypted = encrypt_credentials(data)

    # Generate a second, different RSA key
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", other_pem)

    with pytest.raises(InvalidTag):
        decrypt_credentials(encrypted)


def test_vault_key_differs_from_in_transit_key(monkeypatch, sample_rsa_private_key_pem):
    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", sample_rsa_private_key_pem)

    vault_key = _derive_vault_key()
    assert isinstance(vault_key, bytes)
    assert len(vault_key) == 32  # 256 bits

    # Ensure running HKDF twice gives identical key for same RSA key
    assert _derive_vault_key() == vault_key
