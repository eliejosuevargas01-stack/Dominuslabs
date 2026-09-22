"""Gerenciador de configuração MQTT (AES-ECB decriptação)."""
import base64
import hashlib
import json
import logging
import time
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import httpx

from app.pedidos10.constants import BASE_URL, TOKEN_SERVER, ID_ORIGEM, NUM_VERSAO, DES_VERSAO, AES_ECB_KEY, CHROME_HEADERS
from app.pedidos10.schemas import MqttConfig, Pedidos10Session

logger = logging.getLogger("pedidos10.config_manager")

# Cache de config-env com TTL longo (raramente muda)
_config_cache: dict = {}
_CONFIG_CACHE_TTL = 24 * 3600


def _qt(token_u: str) -> str:
    """Gera qt() = hash de token_u + timestamp."""
    ts = int(time.time() * 1000)
    raw = f"{token_u}:{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _decrypt_aes_ecb(ciphertext_b64: str) -> dict:
    """
    Decripta config-env usando AES-ECB + PKCS7.
    Ordem correta: base64_decode → AES_decrypt → PKCS7_unpad
    Chave: AES_ECB_KEY, padding para 32 bytes com \x00.
    """
    # Derivar chave de 256 bits
    key = AES_ECB_KEY.encode().ljust(32, b"\x00")[:32]

    # 1. Decode base64
    ciphertext = base64.b64decode(ciphertext_b64)

    # 2. AES ECB mode decrypt PRIMEIRO
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # 3. Remover PKCS7 padding DEPOIS
    unpadder = padding.PKCS7(128).unpadder()
    try:
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    except ValueError:
        raise ValueError("Invalid PKCS7 padding")

    # JSON decode
    return json.loads(plaintext.decode("utf-8"))


class ConfigManager:
    """Gerencia busca e decriptação de config-env MQTT."""

    def __init__(self):
        self._config_cache: dict = {}

    async def get_mqtt_config(self, session: Pedidos10Session) -> MqttConfig:
        """
        Busca config-env e decripta para MqttConfig.
        Cache de 24h. Fallback: se falhar retorna MqttConfig vazia.
        """
        # Verifica cache
        cache_key = session.token_u
        now = time.time()
        if cache_key in self._config_cache:
            cached = self._config_cache[cache_key]
            if now - cached["timestamp"] < _CONFIG_CACHE_TTL:
                return cached["config"]

        # Busca config-env — URL padrão sem hash
        url = f"{BASE_URL}/config-env/token-server/{TOKEN_SERVER}/id-origem/{ID_ORIGEM}/num-versao/{NUM_VERSAO}/des-versao/{DES_VERSAO}/token-u/{session.token_u}"
        headers = {
            "authorization": session.jwt,
            "x-token": TOKEN_SERVER,
            **{k: v for k, v in CHROME_HEADERS.items() if k != "content-type"},
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            logger.warning("Request error during config-env: %s. Fallback to polling.", str(e))
            config = MqttConfig(mqtt_region="", mqtt_endpoint="", mqtt_key_id="", mqtt_secret_key="")
            self._config_cache[cache_key] = {"config": config, "timestamp": now}
            return config

        if response.status_code == 401:
            logger.warning("Session expired on config-env request. Fallback to polling.")
            config = MqttConfig(mqtt_region="", mqtt_endpoint="", mqtt_key_id="", mqtt_secret_key="")
            self._config_cache[cache_key] = {"config": config, "timestamp": now}
            return config

        if not response.is_success:
            logger.warning("config-env failed: %s. Fallback to polling.", response.text)
            config = MqttConfig(mqtt_region="", mqtt_endpoint="", mqtt_key_id="", mqtt_secret_key="")
            self._config_cache[cache_key] = {"config": config, "timestamp": now}
            return config

        data = response.json()
        encrypted_data = data.get("data", "")

        # Decripta
        try:
            decrypted = _decrypt_aes_ecb(encrypted_data)
            config = MqttConfig(
                mqtt_region=decrypted.get("mqtt_region", ""),
                mqtt_endpoint=decrypted.get("mqtt_endpoint", ""),
                mqtt_key_id=decrypted.get("mqtt_key_id", ""),
                mqtt_secret_key=decrypted.get("mqtt_secret_key", ""),
            )
            self._config_cache[cache_key] = {"config": config, "timestamp": now}
            return config
        except Exception as e:
            logger.warning("AES-ECB decryption failed: %s. Fallback to polling.", str(e))
            config = MqttConfig(mqtt_region="", mqtt_endpoint="", mqtt_key_id="", mqtt_secret_key="")
            self._config_cache[cache_key] = {"config": config, "timestamp": now}
            return config

    def invalidate_cache(self, token_u: str):
        """Invalida config-cache para token_u."""
        if token_u in self._config_cache:
            del self._config_cache[token_u]
