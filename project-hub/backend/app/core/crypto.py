import os
import json
import base64
import logging
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key,
    load_pem_private_key,
)
from cryptography.exceptions import InvalidTag

from app.core.config import settings

logger = logging.getLogger("crypto")


def clean_pem(pem_str: str) -> bytes:
    """Cleans up a PEM string and converts it to bytes."""
    if not pem_str:
        return b""
    cleaned = pem_str.strip().strip('"').strip("'").replace("\\n", "\n").strip()
    if not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned.encode("utf-8")


def get_public_key(target: str) -> Optional[bytes]:
    """Returns the corresponding public key based on the target name."""
    if target == "whats-api":
        return clean_pem(settings.WHATS_API_PUBLIC_KEY)
    elif target == "idpw":
        return clean_pem(settings.IDPW_PUBLIC_KEY)
    elif target == "n8n":
        return clean_pem(settings.N8N_PUBLIC_KEY)
    elif target == "dominus":
        return clean_pem(settings.DOMINUS_PUBLIC_KEY)
    return None


def encrypt_payload(payload_dict: Dict[str, Any], target: str) -> Dict[str, Any]:
    """
    Encrypts a JSON payload using Hybrid Encryption (AES-256-GCM + RSA-OAEP).
    """
    target_public_key_pem = get_public_key(target)
    if not target_public_key_pem:
        logger.warning(f"No public key found for target: {target}. Returning original payload.")
        return payload_dict
        
    try:
        # Load the public key
        public_key = load_pem_public_key(target_public_key_pem)

        # 1. Generate strong symmetric AES-256 key (32 bytes) and IV (16 bytes)
        aes_key = AESGCM.generate_key(bit_length=256)
        iv = os.urandom(16)

        # 2. Encrypt the real JSON payload using AES-256-GCM
        aesgcm = AESGCM(aes_key)
        payload_bytes = json.dumps(payload_dict).encode('utf-8')
        
        # AESGCM.encrypt returns ciphertext + auth tag concatenated.
        # We need to split them. The tag is the last 16 bytes.
        encrypted_data = aesgcm.encrypt(iv, payload_bytes, None)
        ciphertext = encrypted_data[:-16]
        auth_tag = encrypted_data[-16:]

        # 3. Encrypt the AES-256 key using RSA-OAEP (SHA-256)
        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 4. Return the formatted JSON object with Base64 values
        return {
            "_encrypted": True,
            "encryptedKey": base64.b64encode(encrypted_key).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "authTag": base64.b64encode(auth_tag).decode('utf-8'),
            "payload": base64.b64encode(ciphertext).decode('utf-8')
        }

    except Exception as e:
        logger.error(f"Error encrypting payload for {target}: {e}")
        # In case of error, you might want to raise it or just return the original payload
        # depending on security strictness. For Zero-Trust, raising is better.
        raise e


def decrypt_payload(encrypted_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypts a Hybrid Encrypted JSON payload (AES-256-GCM + RSA-OAEP) using Dominus Private Key.
    """
    if not encrypted_dict.get("_encrypted"):
        return encrypted_dict
        
    private_key_pem = clean_pem(settings.DOMINUS_PRIVATE_KEY)
    if not private_key_pem:
        logger.error("DOMINUS_PRIVATE_KEY is not set. Cannot decrypt payload.")
        raise ValueError("Private key missing.")

    try:
        # Load Dominus private key
        private_key = load_pem_private_key(private_key_pem, password=None)

        # 1. Extract values and decode from Base64
        encrypted_key = base64.b64decode(encrypted_dict["encryptedKey"])
        iv = base64.b64decode(encrypted_dict["iv"])
        auth_tag = base64.b64decode(encrypted_dict["authTag"])
        ciphertext = base64.b64decode(encrypted_dict["payload"])

        # 2. Decrypt the AES-256 key using RSA-OAEP
        aes_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 3. Decrypt the payload using AES-256-GCM
        aesgcm = AESGCM(aes_key)
        # AESGCM.decrypt expects ciphertext + auth_tag concatenated
        payload_bytes = aesgcm.decrypt(iv, ciphertext + auth_tag, None)

        # 4. Parse the original JSON
        return json.loads(payload_bytes.decode('utf-8'))

    except InvalidTag:
        logger.error("Authentication tag verification failed. The payload may have been tampered with.")
        raise ValueError("Invalid authentication tag.")
    except Exception as e:
        logger.error(f"Error decrypting payload: {e}")
        raise e
