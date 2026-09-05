import pytest
from app.core.security import get_password_hash, verify_password

def test_password_hashing():
    password = "supersecretpassword123!"
    hashed = get_password_hash(password)

    assert ":" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_verify_password_invalid_hash_format():
    assert verify_password("password", "invalidhash") is False
    assert verify_password("password", "") is False
    assert verify_password("password", "salt_without_hash:") is False
