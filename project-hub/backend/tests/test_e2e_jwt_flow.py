"""
E2E Integration Test: Dominius ⇄ Identity Worker ⇄ WhatsApp API
Valida todo o ciclo de vida M2M utilizando mock explícito HTTP em nível de teste.
"""
import pytest
import asyncio
import jwt
from unittest.mock import patch, AsyncMock
import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount
from app.repositories.user_repo import user_repo
from app.schemas.user import UserCreate
from app.services.identity_service import get_m2m_jwt
from app.services.whatsapp_service import send_whatsapp_message, get_tenant_id_for_user


@pytest.mark.anyio
async def test_full_m2m_flow():
    db: Session = SessionLocal()
    try:
        # 1. Cadastro de Usuário no Dominius (com tenant_id automático)
        test_email = "test_tenant_e2e@dominuslabs.online"
        existing_user = user_repo.get_by_email(db, test_email)
        if existing_user:
            user_repo.remove(db, existing_user.id)

        user_in = UserCreate(
            email=test_email,
            password="securepassword123",
            role="custom",
            can_manage_crm=True
        )
        user = user_repo.create(db, user_in)
        assert user.id is not None
        assert user.tenant_id is not None
        assert user.tenant_id.startswith("tenant_")
        print(f"\n[E2E-TEST] 1. Usuário criado: user_id={user.id}, tenant_id={user.tenant_id}")

        # 2. Provisionamento da conta WhatsApp vinculada ao tenant_id
        import uuid
        from app.models.whatsapp_account import WhatsappAccount
        wa_account = WhatsappAccount(
            user_id=user.id,
            tenant_id=user.tenant_id,
            session_id="test_session_id"
        )
        db.add(wa_account)
        db.commit()
        print(f"[E2E-TEST] 2. Conta WhatsApp vinculada ao tenant_id={user.tenant_id}")

        # Mock das respostas M2M do Identity Worker e da WhatsApp API para os testes unitários
        fake_jwt = jwt.encode(
            {
                "iss": "https://identity.dominus.online",
                "aud": "whatsapp-api",
                "sub": "dominus-prod",
                "tenant_id": user.tenant_id,
                "scope": "whatsapp:messages:send",
                "exp": 1900000000
            },
            "secret_key_long_enough_for_sha256_32bytes",
            algorithm="HS256"
        )

        from app.core.crypto import encrypt_payload

        async def mock_post(url, **kwargs):
            if "tokens" in url:
                encrypted_resp = encrypt_payload(
                    {"access_token": fake_jwt, "expires_in": 300},
                    target="dominus"
                )
                return httpx.Response(200, json=encrypted_resp)
            elif "messages/send" in url:
                return httpx.Response(200, json={"status": "success", "message_id": f"msg_{user.tenant_id}"})
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

            # 3. Solicitação do JWT M2M ao Identity Worker
            scope = "whatsapp:messages:send"
            token = await get_m2m_jwt(tenant_id=user.tenant_id, scope=scope)
            assert token is not None
            print(f"[E2E-TEST] 3. JWT M2M obtido com sucesso do Identity Worker")

            # 4. Inspeção e validação das claims do JWT
            decoded = jwt.decode(token, options={"verify_signature": False})
            assert decoded["iss"] == "https://identity.dominus.online"
            assert decoded["aud"] == "whatsapp-api"
            assert decoded["sub"] == "dominus-prod"
            assert decoded["tenant_id"] == user.tenant_id
            assert decoded["scope"] == scope
            print(f"[E2E-TEST] 4. Claims JWT validadas: iss={decoded['iss']}, tenant_id={decoded['tenant_id']}, scope={decoded['scope']}")

            # 5. Envio de Mensagem pela WhatsApp API
            res = await send_whatsapp_message(
                user=user,
                db=db,
                to_phone="5511999998888",
                message_text="Olá! Teste JWT M2M Dominius.",
                session_id="test_session_id"
            )
            assert res is not None
            assert res.get("status") == "success"
            print(f"[E2E-TEST] 5. Resposta do Envio: {res}")

        print("\n✅ [E2E-TEST] Todos os passos do fluxo M2M JWT foram validados com SUCESSO!")
    finally:
        # Cleanup
        existing_user = user_repo.get_by_email(db, test_email)
        if existing_user:
            user_repo.remove(db, existing_user.id)
        db.close()


@pytest.mark.anyio
async def test_idpw_plaintext_response_rejected_with_502():
    """Valida que resposta em texto claro do IDPW é sumariamente rejeitada com 502 (fail-closed)."""
    from app.services.identity_client import identity_client
    from fastapi import HTTPException

    # Clear identity client cache
    identity_client._cache.clear()

    mock_client_instance = AsyncMock()
    # Retorna JSON sem chave '_encrypted: True'
    mock_client_instance.post.return_value = httpx.Response(
        200,
        json={"access_token": "plaintext_token", "expires_in": 300}
    )

    with patch("app.services.identity_client.get_async_client") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(HTTPException) as exc_info:
            await identity_client.get_token(tenant_id="test_tenant_plaintext", scope="whatsapp:messages:send")
        assert exc_info.value.status_code == 502
        assert "criptografia obrigatória" in exc_info.value.detail


@pytest.mark.anyio
async def test_crypto_and_identity_client_fail_closed_when_keys_missing(monkeypatch):
    """Valida que ausência de chaves criptográficas dispara erro imediatamente (fail-closed)."""
    from app.core.config import settings
    from app.core import crypto
    from app.services.identity_client import identity_client
    from fastapi import HTTPException

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
async def test_identity_client_sends_single_encrypted_payload():
    """Valida que o IdentityClient envia payload com criptografia única (não duplamente criptografado)."""
    from app.services.identity_client import identity_client
    from app.core.crypto import decrypt_payload, encrypt_payload

    identity_client._cache.clear()

    captured_requests = []

    async def mock_post(url, **kwargs):
        captured_requests.append(kwargs)
        fake_jwt = jwt.encode(
            {"iss": "https://identity.dominus.online", "tenant_id": "tenant_single_enc", "exp": 1900000000},
            "secret_key_long_enough_for_sha256_32bytes",
            algorithm="HS256"
        )
        encrypted_resp = encrypt_payload(
            {"access_token": fake_jwt, "expires_in": 300},
            target="dominus"
        )
        return httpx.Response(200, json=encrypted_resp)

    mock_client_instance = AsyncMock()
    mock_client_instance.post = mock_post

    with patch("app.services.identity_client.get_async_client") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        token = await identity_client.get_token(tenant_id="tenant_single_enc", scope="whatsapp:messages:send")
        assert token is not None

        assert len(captured_requests) == 1
        req_json = captured_requests[0].get("json")
        assert req_json is not None
        assert req_json.get("_encrypted") is True
        assert "encryptedKey" in req_json
        assert "iv" in req_json
        assert "payload" in req_json

        # Decifrando o payload UMA vez deve recuperar os dados em claro (prova de criptografia única, sem dupla camada)
        decrypted = decrypt_payload(req_json)
        assert isinstance(decrypted, dict)
        assert decrypted.get("tenant_id") == "tenant_single_enc"
        assert decrypted.get("scope") == "whatsapp:messages:send"
        assert "timestamp" in decrypted


@pytest.mark.anyio
async def test_whatsapp_client_payload_encryption_and_decryption(monkeypatch):
    """Valida que o WhatsAppClient criptografa payloads enviados e decriptografa respostas criptografadas."""
    from app.services.whatsapp_client import whatsapp_client
    from app.core.crypto import decrypt_payload, encrypt_payload
    from app.core.config import settings

    captured_wa_requests = []

    async def mock_request(method, url, **kwargs):
        captured_wa_requests.append(kwargs)
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
        sent_json = captured_wa_requests[0].get("json")
        assert sent_json is not None
        assert sent_json.get("_encrypted") is True

        # Decriptografia do payload enviado comprova que foi cifrado para whats-api e contém dados corretos
        decrypted_sent = decrypt_payload(sent_json)
        assert decrypted_sent["chatId"] == "5511999998888@c.us"
        assert decrypted_sent["text"] == "Mensagem segura para WhatsApp"
        assert decrypted_sent["session"] == "session_wa_test"


@pytest.mark.anyio
async def test_whatsapp_client_fail_closed_when_key_missing(monkeypatch):
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


if __name__ == "__main__":
    asyncio.run(test_full_m2m_flow())


