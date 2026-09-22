"""Gerenciador de autenticação Pedidos10 com reauth automático."""
import logging
import time
from typing import Optional
import httpx

from app.core.config import settings
from app.core.credential_vault import encrypt_credentials, decrypt_credentials
from app.pedidos10.constants import (
    BASE_URL,
    TOKEN_SERVER,
    APP_NAME,
    ID_ORIGEM,
    NUM_VERSAO,
    DES_VERSAO,
    CHROME_HEADERS,
)
from app.pedidos10.schemas import (
    Pedidos10Credentials,
    Pedidos10Session,
    UsuarioResponse,
    AuthResponse,
    ErrorResponse,
)

logger = logging.getLogger("pedidos10.auth_manager")

# Cache de sessão com TTL de 23h (JWT Pedidos10 expira em 24h)
_session_cache: dict = {}
_SESSION_CACHE_TTL = 23 * 3600


class AuthManager:
    """Gerencia login, sessão e reauth Pedidos10."""

    def __init__(self):
        self._session_cache: dict = {}

    async def login(self, credentials: Pedidos10Credentials) -> Pedidos10Session:
        """
        Faz login no Pedidos10 e retorna sessão (JWT + token-u).
        HTTP 400 = credenciais inválidas, HTTP 401 = token expirado.
        """
        payload = {
            "des_login": credentials.email,
            "des_senha": credentials.password.get_secret_value(),
            "des_recaptcha_token": "",
            "app_name": APP_NAME,
            "id_origem": ID_ORIGEM,
            "num_versao": NUM_VERSAO,
            "des_versao": DES_VERSAO,
            "token-server": TOKEN_SERVER,
            "token-u": None,
        }
        headers = {**CHROME_HEADERS, "content-type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{BASE_URL}/auth",
                    json=payload,
                    headers=headers,
                )
        except httpx.RequestError as e:
            logger.error("Request error during login: %s", str(e))
            raise ConnectionError(f"Failed to connect: {e}")

        if response.status_code == 400:
            logger.error("Invalid credentials for email: %s", credentials.email[:3] + "***")
            raise ValueError("Credenciais inválidas")
        if response.status_code == 401:
            logger.warning("Token expirado ou inválido para email: %s", credentials.email[:3] + "***")
            raise ValueError("Token expirado ou inválido")
        if not response.is_success:
            logger.error("Login failed with status %d for email: %s", response.status_code, credentials.email[:3] + "***")
            raise ConnectionError(f"Login failed: {response.text}")

        data = response.json()
        # API retorna {"data": {"jwt": ..., "des_token": ...}} ou {"jwt": ..., "des_token": ...}
        inner = data.get("data", data)
        return Pedidos10Session(
            jwt=inner["jwt"],
            token_u=inner["des_token"],
        )

    async def get_user_info(self, session: Pedidos10Session) -> UsuarioResponse:
        """Busca informações do usuário e lista de merchants."""
        url = f"{BASE_URL}/usuario/token-server/{TOKEN_SERVER}/id-origem/{ID_ORIGEM}/num-versao/{NUM_VERSAO}/des-versao/{DES_VERSAO}/token-u/{session.token_u}"
        headers = {
            **CHROME_HEADERS,
            "authorization": session.jwt,
            "x-token": TOKEN_SERVER,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            logger.error("Request error during get_user_info: %s", str(e))
            raise ConnectionError(f"Failed to connect: {e}")

        if response.status_code == 401:
            raise ValueError("Session expired - reauth required")
        if not response.is_success:
            raise ConnectionError(f"get_user_info failed: {response.text}")

        data = response.json()
        # API retorna {"data": {"id": ..., "estabelecimentos": [...]}}
        inner = data.get("data", data)
        return UsuarioResponse(
            id_estabelecimento=str(inner.get("id", "")),
            des_estabelecimento=inner.get("des_usuario", ""),
            merchants=inner.get("estabelecimentos", []),
        )

    async def get_session(self, credentials_enc: str) -> Pedidos10Session:
        """
        Recupera sessão de DB ou cache, renovando se expirada.
        Credenciais são criptografadas via credential_vault.
        """
        try:
            decrypted = decrypt_credentials(credentials_enc)
        except Exception as e:
            logger.error("Failed to decrypt credentials: %s", str(e))
            raise ValueError("Failed to decrypt credentials")

        credentials = Pedidos10Credentials(email=decrypted["email"], password=decrypted["password"])

        # Verifica cache
        cache_key = credentials.email
        now = time.time()
        if cache_key in self._session_cache:
            cached = self._session_cache[cache_key]
            if now - cached["timestamp"] < _SESSION_CACHE_TTL:
                return cached["session"]

        # Faz login
        session = await self.login(credentials)
        self._session_cache[cache_key] = {"session": session, "timestamp": now}
        return session

    async def refresh(self, credentials_enc: str) -> Pedidos10Session:
        """Força novo login, invalidando cache."""
        # Remove do cache
        try:
            decrypted = decrypt_credentials(credentials_enc)
        except Exception:
            raise ValueError("Failed to decrypt credentials")

        email = decrypted["email"]
        if email in self._session_cache:
            del self._session_cache[email]

        return await self.login(Pedidos10Credentials(email=email, password=decrypted["password"]))

    async def store_credentials(self, email: str, password: str) -> str:
        """Criptografa credenciais e returna string encriptada para DB."""
        data = {"email": email, "password": password}
        return encrypt_credentials(data)

    @staticmethod
    def _qt(token_u: str) -> str:
        """Gera qt() = hash de token_u + timestamp."""
        import hashlib
        ts = int(time.time() * 1000)
        raw = f"{token_u}:{ts}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def invalidate_cache(self, email: str):
        """Invalida sessão em cache para email."""
        if email in self._session_cache:
            del self._session_cache[email]
