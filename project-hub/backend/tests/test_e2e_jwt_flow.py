"""
E2E Integration Test: Dominius ⇄ Identity Worker ⇄ WhatsApp API
Valida todo o ciclo de vida M2M utilizando mock explícito HTTP em nível de teste.
"""
import base64
import json
import logging
import time
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from app.core.config import settings
from app.models.whatsapp_account import WhatsappAccount
from app.repositories.user_repo import user_repo
from app.schemas.user import UserCreate
from app.services.identity_client import IdentityClient, identity_client
from app.services.whatsapp_service import send_whatsapp_message


LOGICAL_PAYLOAD_FIELDS = {
    "aud",
    "tenant_id",
    "scope",
    "request_id",
    "timestamp",
    "nonce",
    "jti",
}
SIGNED_ENVELOPE_FIELDS = LOGICAL_PAYLOAD_FIELDS | {"payload", "signature", "algorithm"}
ENCRYPTED_TRANSPORT_FIELDS = {"_encrypted", "encryptedKey", "iv", "authTag", "payload"}


def _new_rsa_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_key, private_pem, public_pem


def _decrypt_transport_independently(envelope, recipient_private_key):
    """Abre o wrapper sem reutilizar o decryptor da aplicação."""
    assert set(envelope) == ENCRYPTED_TRANSPORT_FIELDS
    assert envelope["_encrypted"] is True

    encrypted_key = base64.b64decode(envelope["encryptedKey"], validate=True)
    iv = base64.b64decode(envelope["iv"], validate=True)
    auth_tag = base64.b64decode(envelope["authTag"], validate=True)
    ciphertext = base64.b64decode(envelope["payload"], validate=True)
    aes_key = recipient_private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    assert len(aes_key) == 32
    assert len(iv) == 16
    assert len(auth_tag) == 16
    plaintext = AESGCM(aes_key).decrypt(iv, ciphertext + auth_tag, None)
    return json.loads(plaintext.decode("utf-8"))


@pytest.fixture
def identity_crypto_material(monkeypatch):
    """Instala chaves distintas e efêmeras para cada fronteira criptográfica."""
    dominus_key, dominus_private_pem, dominus_public_pem = _new_rsa_material()
    idpw_key, _, idpw_public_pem = _new_rsa_material()
    whats_api_key, _, whats_api_public_pem = _new_rsa_material()

    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", dominus_private_pem)
    monkeypatch.setattr(settings, "DOMINUS_PUBLIC_KEY", dominus_public_pem)
    monkeypatch.setattr(settings, "IDPW_PUBLIC_KEY", idpw_public_pem)
    monkeypatch.setattr(settings, "WHATS_API_PUBLIC_KEY", whats_api_public_pem)
    identity_client._cache.clear()
    yield {
        "dominus": dominus_key,
        "idpw": idpw_key,
        "whats_api": whats_api_key,
    }
    identity_client._cache.clear()


@pytest.mark.anyio
async def test_full_m2m_flow(db, identity_crypto_material):
    # O banco transacional da fixture impede qualquer escrita no banco local/dev.
    test_email = f"test_tenant_e2e_{uuid.uuid4().hex}@dominuslabs.online"
    user = user_repo.create(
        db,
        UserCreate(
            email=test_email,
            password="securepassword123",
            role="custom",
            can_manage_crm=True,
        ),
    )
    assert user.id is not None
    assert user.tenant_id is not None
    assert user.tenant_id.startswith("tenant_")

    wa_account = WhatsappAccount(
        user_id=user.id,
        tenant_id=user.tenant_id,
        session_id=f"test_session_{uuid.uuid4().hex}",
    )
    db.add(wa_account)
    db.commit()

    fake_jwt = jwt.encode(
        {
            "iss": "https://identity.dominus.online",
            "aud": "whatsapp-api",
            "sub": "dominus-prod",
            "tenant_id": user.tenant_id,
            "scope": "whatsapp:messages:send",
            "exp": int(time.time()) + 3600,
        },
        identity_crypto_material["idpw"],
        algorithm="RS256",
    )

    from app.core.crypto import encrypt_payload

    async def mock_post(url, **kwargs):
        if "tokens" in url:
            encrypted_resp = encrypt_payload(
                {"access_token": fake_jwt, "expires_in": 300},
                target="dominus",
            )
            return httpx.Response(200, json=encrypted_resp)
        if "messages/send" in url:
            return httpx.Response(
                200,
                json={"status": "success", "message_id": f"msg_{user.tenant_id}"},
            )
        return httpx.Response(404, json={"detail": "Not found"})

    mock_client_instance = AsyncMock()
    mock_client_instance.post = mock_post

    async def mock_request(method, url, **kwargs):
        return await mock_post(url, **kwargs)

    mock_client_instance.request = mock_request

    with patch("app.services.identity_client.get_async_client") as mock_async_client, \
         patch("app.services.whatsapp_client.get_async_client") as mock_async_client_wa:
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        mock_async_client_wa.return_value.__aenter__.return_value = mock_client_instance

        scope = "whatsapp:messages:send"
        token = await identity_client.get_token(tenant_id=user.tenant_id, scope=scope)
        decoded = jwt.decode(
            token,
            identity_crypto_material["idpw"].public_key(),
            algorithms=["RS256"],
            audience="whatsapp-api",
            issuer="https://identity.dominus.online",
        )
        assert decoded["sub"] == "dominus-prod"
        assert decoded["tenant_id"] == user.tenant_id
        assert decoded["scope"] == scope

        res = await send_whatsapp_message(
            user=user,
            db=db,
            to_phone="5511999998888",
            message_text="Olá! Teste JWT M2M Dominius.",
            session_id=wa_account.session_id,
        )
        assert res == {"status": "success", "message_id": f"msg_{user.tenant_id}"}


@pytest.mark.anyio
async def test_idpw_plaintext_response_rejected_with_502(identity_crypto_material):
    """Valida que resposta em texto claro do IDPW é sumariamente rejeitada com 502 (fail-closed)."""
    client = IdentityClient()

    mock_client_instance = AsyncMock()
    # Retorna JSON sem chave '_encrypted: True'
    mock_client_instance.post.return_value = httpx.Response(
        200,
        json={"access_token": "plaintext_token", "expires_in": 300}
    )

    with patch("app.services.identity_client.get_async_client") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(HTTPException) as exc_info:
            await client.get_token(tenant_id="test_tenant_plaintext", scope="whatsapp:messages:send")
        assert exc_info.value.status_code == 502
        assert "criptografia obrigatória" in exc_info.value.detail
        assert not client._cache


@pytest.mark.parametrize(
    "decrypted_response",
    [
        {"expires_in": 300},
        {"access_token": " ", "expires_in": 300},
        {"access_token": {"token": "issued-token"}, "expires_in": 300},
        {"access_token": "issued-token"},
        {"access_token": "issued-token", "expires_in": 0},
        {"access_token": "issued-token", "expires_in": -1},
        {"access_token": "issued-token", "expires_in": "300"},
        {"access_token": "issued-token", "expires_in": True},
    ],
    ids=(
        "missing-access-token",
        "blank-access-token",
        "non-string-access-token",
        "missing-expires-in",
        "zero-expires-in",
        "negative-expires-in",
        "string-expires-in",
        "boolean-expires-in",
    ),
)
@pytest.mark.anyio
async def test_idpw_incomplete_or_invalid_response_rejected_with_502(
    decrypted_response,
    identity_crypto_material,
):
    """Credenciais incompletas ou com validade inválida nunca entram no cache M2M."""
    from app.core.crypto import encrypt_payload

    client = IdentityClient()
    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = httpx.Response(
        200,
        json=encrypt_payload(decrypted_response, target="dominus"),
    )

    with patch("app.services.identity_client.get_async_client") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(HTTPException) as exc_info:
            await client.get_token(
                tenant_id="tenant_invalid_response",
                scope="whatsapp:messages:send",
            )

    assert exc_info.value.status_code == 502
    assert not client._cache


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_id", " "),
        ("tenant_id", " tenant_valid"),
        ("tenant_id", 123),
        ("scope", " "),
        ("scope", "whatsapp:messages:send "),
        ("scope", ["whatsapp:messages:send"]),
        ("aud", " "),
        ("aud", " whatsapp-api"),
        ("aud", None),
    ],
)
@pytest.mark.anyio
async def test_identity_client_rejects_invalid_logical_fields(field, value):
    """Campos do payload lógico precisam ser strings não vazias antes de qualquer I/O."""
    arguments = {
        "tenant_id": "tenant_valid",
        "scope": "whatsapp:messages:send",
        "aud": "whatsapp-api",
    }
    arguments[field] = value
    client = IdentityClient()

    with patch("app.services.identity_client.get_async_client") as mock_async_client:
        with pytest.raises(HTTPException) as exc_info:
            await client.get_token(**arguments)

    assert exc_info.value.status_code == 400
    mock_async_client.assert_not_called()
    assert not client._cache


@pytest.mark.anyio
async def test_crypto_and_identity_client_fail_closed_when_keys_missing(
    monkeypatch,
    identity_crypto_material,
):
    """Valida que ausência de chaves criptográficas dispara erro imediatamente (fail-closed)."""
    from app.core.config import settings
    from app.core import crypto
    identity_client._cache.clear()

    # 1. Ausência de DOMINUS_PRIVATE_KEY no crypto.sign_payload deve lançar ValueError
    monkeypatch.setattr(settings, "DOMINUS_PRIVATE_KEY", "")
    with pytest.raises(ValueError) as exc_sign:
        crypto.sign_payload({"test": "data"})
    assert "DOMINUS_PRIVATE_KEY não configurada" in str(exc_sign.value)

    # 2. Ausência de chave pública de destino no crypto.encrypt_payload deve lançar ValueError
    monkeypatch.setattr(settings, "IDPW_PUBLIC_KEY", "")
    with pytest.raises(ValueError) as exc_enc:
        crypto.encrypt_payload({"test": "data"}, target="idpw")
    assert "Chave pública não configurada" in str(exc_enc.value)

    # 3. Ausência de chaves no IdentityClient deve levantar 500
    with pytest.raises(HTTPException) as exc_client:
        await identity_client.get_token(tenant_id="test_tenant", scope="test:scope")
    assert exc_client.value.status_code == 500
    assert "DOMINUS_PRIVATE_KEY ausente" in exc_client.value.detail


@pytest.mark.anyio
async def test_identity_client_emits_frozen_signed_and_encrypted_contract(
    monkeypatch,
    identity_crypto_material,
    caplog,
):
    """Prova o contrato HTTP, criptográfico e lógico congelado do IdentityClient."""
    from app.core.crypto import encrypt_payload

    client = IdentityClient()
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(settings, "IDENTITY_WORKER_URL", "https://idpw.example.test/")

    captured_requests = []

    async def mock_post(url, **kwargs):
        captured_requests.append((url, kwargs))
        encrypted_resp = encrypt_payload(
            {"access_token": "issued-m2m-token", "expires_in": 300},
            target="dominus"
        )
        return httpx.Response(200, json=encrypted_resp)

    mock_client_instance = AsyncMock()
    mock_client_instance.post = mock_post

    with patch("app.services.identity_client.get_async_client") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        token = await client.get_token(
            tenant_id="tenant_single_enc",
            scope="whatsapp:messages:send",
            aud="whatsapp-api",
        )
        assert token == "issued-m2m-token"

        assert len(captured_requests) == 1
        request_url, request_kwargs = captured_requests[0]
        assert request_url == "https://idpw.example.test/v1/tokens"
        assert set(request_kwargs) == {"json", "headers"}

        req_json = request_kwargs["json"]
        assert set(req_json) == ENCRYPTED_TRANSPORT_FIELDS
        assert req_json["_encrypted"] is True

        # Uma única abertura independente recupera o envelope lógico assinado.
        decrypted = _decrypt_transport_independently(
            req_json,
            identity_crypto_material["idpw"],
        )
        assert set(decrypted) == SIGNED_ENVELOPE_FIELDS
        assert decrypted["algorithm"] == "RS256"

        payload = decrypted["payload"]
        assert set(payload) == LOGICAL_PAYLOAD_FIELDS
        assert payload["aud"] == "whatsapp-api"
        assert payload["tenant_id"] == "tenant_single_enc"
        assert payload["scope"] == "whatsapp:messages:send"
        for field in LOGICAL_PAYLOAD_FIELDS:
            assert decrypted[field] == payload[field]

        assert isinstance(payload["timestamp"], int)
        assert not isinstance(payload["timestamp"], bool)
        assert payload["timestamp"] > 0
        assert uuid.UUID(payload["request_id"])
        assert uuid.UUID(payload["jti"])
        assert len(payload["nonce"]) == 32
        int(payload["nonce"], 16)

        canonical_payload = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = base64.b64decode(decrypted["signature"], validate=True)
        identity_crypto_material["dominus"].public_key().verify(
            signature,
            canonical_payload,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        assert request_kwargs["headers"] == {
            "Content-Type": "application/json",
            "X-Request-ID": payload["request_id"],
        }
        assert dict(client._cache) == {
            ("tenant_single_enc", "whatsapp:messages:send", "whatsapp-api"): "issued-m2m-token"
        }
        assert "issued-m2m-token" not in caplog.text


@pytest.mark.anyio
async def test_whatsapp_client_payload_encryption_and_decryption(
    monkeypatch,
    identity_crypto_material,
):
    """Valida que o WhatsAppClient criptografa payloads enviados e decriptografa respostas criptografadas."""
    from app.services.whatsapp_client import whatsapp_client
    from app.core.crypto import encrypt_payload
    from app.core.config import settings

    captured_wa_requests = []

    async def mock_request(method, url, **kwargs):
        captured_wa_requests.append((method, url, kwargs))
        # Retorna resposta criptografada
        encrypted_resp = encrypt_payload({"status": "success", "message_id": "wa_msg_123"}, target="dominus")
        return httpx.Response(200, json=encrypted_resp, headers={"content-type": "application/json"})

    mock_client_instance = AsyncMock()
    mock_client_instance.request = mock_request

    with patch("app.services.whatsapp_client.identity_client.get_token", new_callable=AsyncMock) as mock_get_token, \
         patch("app.services.whatsapp_client.get_async_client") as mock_async_client:

        mock_get_token.return_value = "fake_m2m_jwt_for_wa"
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await whatsapp_client.send_message(
            tenant_id="tenant_wa_test",
            session_id="session_wa_test",
            message_data={
                "chatId": "5511999998888@c.us",
                "text": "Mensagem segura para WhatsApp",
                "session": "session_wa_test"
            }
        )

        assert result == {"status": "success", "message_id": "wa_msg_123"}
        assert len(captured_wa_requests) == 1
        request_method, request_url, request_kwargs = captured_wa_requests[0]
        sent_json = request_kwargs.get("json")
        assert sent_json is not None
        assert sent_json.get("_encrypted") is True

        assert request_method == "POST"
        assert request_url.endswith("/api/sessions/session_wa_test/messages/send")
        assert request_kwargs.get("params") is None
        assert request_kwargs["headers"]["Authorization"] == "Bearer fake_m2m_jwt_for_wa"
        assert set(request_kwargs["headers"]) == {
            "Authorization",
            "X-Request-ID",
            "Idempotency-Key",
        }
        assert "fake_m2m_jwt_for_wa" not in request_url
        assert "fake_m2m_jwt_for_wa" not in json.dumps(sent_json)

        # Abertura independente comprova o destinatário e os parâmetros criptográficos.
        decrypted_sent = _decrypt_transport_independently(
            sent_json,
            identity_crypto_material["whats_api"],
        )
        assert decrypted_sent["chatId"] == "5511999998888@c.us"
        assert decrypted_sent["text"] == "Mensagem segura para WhatsApp"
        assert decrypted_sent["session"] == "session_wa_test"


@pytest.mark.anyio
async def test_whatsapp_client_fail_closed_when_key_missing(
    monkeypatch,
    identity_crypto_material,
):
    """Valida fail-closed imediato com HTTP 500 se WHATS_API_PUBLIC_KEY estiver ausente."""
    from app.services.whatsapp_client import whatsapp_client
    from app.core.config import settings
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "WHATS_API_PUBLIC_KEY", "")

    with patch("app.services.whatsapp_client.identity_client.get_token", new_callable=AsyncMock) as mock_get_token:
        mock_get_token.return_value = "fake_token"

        with pytest.raises(HTTPException) as exc_info:
            await whatsapp_client.send_message(
                tenant_id="tenant_wa_test",
                session_id="session_wa_test",
                message_data={
                    "chatId": "5511999998888@c.us",
                    "text": "Tentativa sem chave pública"
                }
            )
        assert exc_info.value.status_code == 500
        assert "Falha de criptografia obrigatória para Whats API" in exc_info.value.detail
