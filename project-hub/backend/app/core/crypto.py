"""
Documentação do módulo crypto.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base crypto.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base crypto funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
import os
import json
import base64
import logging
import re
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


import urllib.parse

def clean_pem(pem_str: str) -> bytes:
    """Sanitizes PEM key strings from environment variables (handles raw, single-line, base64-encoded, url-encoded) and converts to bytes."""
# Lógica de decisão (if): Avalia 'if not pem_str:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not pem_str:
        return b""

    cleaned = pem_str.strip().strip('"').strip("'")

    # 1. Handle URL-encoded PEM strings
# Lógica de decisão (if): Avalia 'if "%2D" in cleaned or "%0A" i...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if "%2D" in cleaned or "%0A" in cleaned or "%3D" in cleaned:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            cleaned = urllib.parse.unquote(cleaned)
        except Exception:
            pass

    # 2. Handle Base64-encoded PEM strings (common in Coolify/Docker envs to avoid newline issues)
# Lógica de decisão (if): Avalia 'if "-----BEGIN" not in cleaned...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if "-----BEGIN" not in cleaned:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            decoded_bytes = base64.b64decode(cleaned)
            decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
# Lógica de decisão (if): Avalia 'if "-----BEGIN" in decoded_str...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if "-----BEGIN" in decoded_str:
                cleaned = decoded_str
        except Exception:
            pass

    cleaned = cleaned.replace("\\n", "\n").replace("\r\n", "\n").strip()

    # 3. Re-format PEM block if lines were collapsed or contain unexpected whitespace
# Lógica de decisão (if): Avalia 'if "-----BEGIN" in cleaned:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if "-----BEGIN" in cleaned:
# Lógica de decisão (if): Avalia 'if "-----END" not in cleaned:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "-----END" not in cleaned:
            logger.error(f"[CRYPTO-PEM-ERROR] ❌ DOMINUS_PRIVATE_KEY está TRUNCADA/INCOMPLETA no ambiente ({len(pem_str)} chars). Falta o cabeçalho -----END PRIVATE KEY-----.")
            print(f"[CRYPTO-PEM-ERROR] ❌ DOMINUS_PRIVATE_KEY está TRUNCADA/INCOMPLETA ({len(pem_str)} chars). Verifique a variável de ambiente no Coolify.", flush=True)

        match = re.search(r"-----BEGIN ([A-Z0-9\s\-]+)-----\s*(.*?)\s*(?:-----END \1-----|$)", cleaned, re.DOTALL | re.IGNORECASE)
# Lógica de decisão (if): Avalia 'if match:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if match:
            header_type = match.group(1).strip().upper()
            raw_body = match.group(2)
            # Remove any non-base64 characters and any internal '=' signs from raw_body
            b64_only = re.sub(r"[^A-Za-z0-9+/]", "", raw_body).strip()
            # Recalculate valid Base64 padding (0, 1, or 2 '=' at the end)
            pad_needed = (4 - (len(b64_only) % 4)) % 4
            body = b64_only + ("=" * pad_needed)
            # Wrap base64 body into RFC-compliant 64-character lines
            formatted_body = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
            cleaned = f"-----BEGIN {header_type}-----\n{formatted_body}\n-----END {header_type}-----\n"

# Lógica de decisão (if): Avalia 'if not cleaned.endswith("\n"):...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned.encode("utf-8")


def get_public_key(target: str) -> Optional[bytes]:
    """Returns the corresponding public key based on the target name."""
# Lógica de decisão (if): Avalia 'if target == "whats-api":...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if target == "whats-api":
        return clean_pem(settings.WHATS_API_PUBLIC_KEY)
    elif target == "idpw":
        return clean_pem(settings.IDPW_PUBLIC_KEY)
    elif target == "n8n":
        key = settings.N8N_PUBLIC_KEY or settings.DOMINUS_PUBLIC_KEY
        return clean_pem(key)
    elif target == "dominus":
        return clean_pem(settings.DOMINUS_PUBLIC_KEY)
    return None


def encrypt_payload(payload_dict: Dict[str, Any], target: str) -> Dict[str, Any]:
    """
    Encrypts a JSON payload using Hybrid Encryption (AES-256-GCM + RSA-OAEP).
    """
    target_public_key_pem = get_public_key(target)
# Lógica de decisão (if): Avalia 'if not target_public_key_pem:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not target_public_key_pem:
        logger.warning(f"No public key found for target: {target}. Returning original payload.")
        return payload_dict
        
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
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
        result = {
            "_encrypted": True,
            "encryptedKey": base64.b64encode(encrypted_key).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "authTag": base64.b64encode(auth_tag).decode('utf-8'),
            "payload": base64.b64encode(ciphertext).decode('utf-8')
        }
# Lógica de decisão (if): Avalia 'if target == "idpw":...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if target == "idpw":
            logger.info("[FLOW-STEP 3] Identity Worker payload encrypted successfully")
            print("[FLOW-STEP 3] Identity Worker payload encrypted successfully", flush=True)
        return result

    except Exception as e:
# Lógica de decisão (if): Avalia 'if target == "idpw":...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if target == "idpw":
            logger.error(f"[FLOW-STEP 3] ERROR: Failed to encrypt Identity Worker payload ({e})")
            print(f"[FLOW-STEP 3] ERROR: Failed to encrypt Identity Worker payload ({e})", flush=True)
        logger.error(f"Error encrypting payload for {target}: {e}")
        raise e


def decrypt_payload(encrypted_data: Any) -> Any:
    """
    Decrypts a Hybrid Encrypted JSON payload (AES-256-GCM + RSA-OAEP) using Dominus Private Key.
    Supports both dict envelopes and list of encrypted envelopes.
    """
# Lógica de decisão (if): Avalia 'if not encrypted_data:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not encrypted_data:
        return encrypted_data

# Lógica de decisão (if): Avalia 'if isinstance(encrypted_data, ...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if isinstance(encrypted_data, list):
# Lógica de decisão (if): Avalia 'if len(encrypted_data) == 1 an...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if len(encrypted_data) == 1 and isinstance(encrypted_data[0], dict) and str(encrypted_data[0].get("_encrypted", "")).lower() == "true":
            return decrypt_payload(encrypted_data[0])
        elif any(isinstance(item, dict) and str(item.get("_encrypted", "")).lower() == "true" for item in encrypted_data):
            return [decrypt_payload(item) if isinstance(item, dict) and str(item.get("_encrypted", "")).lower() == "true" else item for item in encrypted_data]
        return encrypted_data

# Lógica de decisão (if): Avalia 'if not isinstance(encrypted_da...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not isinstance(encrypted_data, dict) or str(encrypted_data.get("_encrypted", "")).lower() != "true":
        return encrypted_data
        
    private_key_pem = clean_pem(settings.DOMINUS_PRIVATE_KEY)
# Lógica de decisão (if): Avalia 'if not private_key_pem:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not private_key_pem:
        logger.error("DOMINUS_PRIVATE_KEY is not set. Cannot decrypt payload.")
        raise ValueError("Private key missing.")

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        # Load Dominus private key with fallback for OpenSSH keys
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            private_key = load_pem_private_key(private_key_pem, password=None)
        except Exception as pem_err:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
            try:
                from cryptography.hazmat.primitives.serialization import load_ssh_private_key
                private_key = load_ssh_private_key(private_key_pem, password=None)
            except Exception:
                logger.error(f"Failed to load DOMINUS_PRIVATE_KEY ({len(private_key_pem)} bytes): {pem_err}")
                raise pem_err

        # 1. Extract values and decode from Base64
        encrypted_key = base64.b64decode(encrypted_data["encryptedKey"])
        iv = base64.b64decode(encrypted_data["iv"])
        auth_tag = base64.b64decode(encrypted_data["authTag"])
        ciphertext = base64.b64decode(encrypted_data["payload"])

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

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            return json.loads(payload_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            # Se não for JSON, retorna a string pura
            return payload_bytes.decode('utf-8')

    except InvalidTag:
        logger.error("Authentication tag verification failed. The payload may have been tampered with.")
        raise ValueError("Invalid authentication tag.")
    except Exception as e:
        logger.error(f"Error decrypting payload: {e}")
        raise ValueError(f"Decryption failed: {e}")
