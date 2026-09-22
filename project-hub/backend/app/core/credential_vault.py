import os
import json
import base64
import logging
from typing import Dict, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.core.config import settings

logger = logging.getLogger("credential_vault")

VAULT_INFO = b"dominus-credential-vault-v1"

def _derive_vault_key() -> bytes:
    """Derive a 256-bit AES key from DOMINUS_PRIVATE_KEY using HKDF.
    Uses the private key's DER bytes as input key material.
    This is a DIFFERENT key than the one used for in-transit encryption."""
    private_key_pem = settings.DOMINUS_PRIVATE_KEY
    if not private_key_pem:
        raise RuntimeError("DOMINUS_PRIVATE_KEY not configured. Credential vault is fail-closed.")
    # Import clean_pem from crypto.py
    from app.core.crypto import clean_pem
    pem_bytes = clean_pem(private_key_pem)
    private_key = load_pem_private_key(pem_bytes, password=None)
    # Use private key DER bytes as IKM
    ikm = private_key.private_bytes(
        encoding=__import__('cryptography.hazmat.primitives.serialization', fromlist=['Encoding']).Encoding.DER,
        format=__import__('cryptography.hazmat.primitives.serialization', fromlist=['PrivateFormat']).PrivateFormat.PKCS8,
        encryption_algorithm=__import__('cryptography.hazmat.primitives.serialization', fromlist=['NoEncryption']).NoEncryption()
    )
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=VAULT_INFO,
    )
    return hkdf.derive(ikm)

def encrypt_credentials(data: Dict[str, Any]) -> str:
    """Encrypt a dict of credentials to a base64 string for DB storage.
    Format: base64(iv + ciphertext_with_tag)"""
    key = _derive_vault_key()
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    plaintext = json.dumps(data, separators=(',', ':')).encode('utf-8')
    ct = aesgcm.encrypt(iv, plaintext, None)
    return base64.b64encode(iv + ct).decode('ascii')

def decrypt_credentials(enc: str) -> Dict[str, Any]:
    """Decrypt a base64 string back to dict of credentials."""
    key = _derive_vault_key()
    raw = base64.b64decode(enc)
    iv = raw[:12]
    ct = raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ct, None)
    return json.loads(plaintext.decode('utf-8'))