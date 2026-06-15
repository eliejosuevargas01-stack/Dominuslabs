import hashlib
import os

def get_password_hash(password: str) -> str:
    """Hash password using PBKDF2 HMAC-SHA256 with 100,000 iterations"""
    salt = os.urandom(16).hex()
    db_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}:{db_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify standard password against PBKDF2 hash"""
    try:
        salt, db_hash = hashed_password.split(':')
        test_hash = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return test_hash == db_hash
    except Exception:
        return False
