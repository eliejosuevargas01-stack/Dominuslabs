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
        wa_account = WhatsappAccount(
            user_id=user.id,
            tenant_id=user.tenant_id,
            client_id="123e4567-e89b-12d3-a456-426614174000",
            client_secret="test_secret_key_12345"
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

        async def mock_post(url, json=None, headers=None):
            if "tokens" in url:
                return httpx.Response(200, json={"access_token": fake_jwt, "expires_in": 300})
            elif "messages/send" in url:
                return httpx.Response(200, json={"status": "success", "message_id": f"msg_{user.tenant_id}"})
            return httpx.Response(404, json={"detail": "Not found"})

        mock_client_instance = AsyncMock()
        mock_client_instance.post = mock_post

        with patch("app.services.identity_service.get_mtls_async_client") as mock_mtls_identity, \
             patch("app.services.whatsapp_service.get_mtls_async_client") as mock_mtls_wa:
            
            mock_mtls_identity.return_value.__aenter__.return_value = mock_client_instance
            mock_mtls_wa.return_value.__aenter__.return_value = mock_client_instance

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
                message_text="Olá! Teste mTLS + JWT M2M Dominius."
            )
            assert res is not None
            assert res.get("status") == "success"
            print(f"[E2E-TEST] 5. Resposta do Envio: {res}")

        print("\n✅ [E2E-TEST] Todos os passos do fluxo M2M mTLS + JWT foram validados com SUCESSO!")
    finally:
        # Cleanup
        existing_user = user_repo.get_by_email(db, test_email)
        if existing_user:
            user_repo.remove(db, existing_user.id)
        db.close()


if __name__ == "__main__":
    asyncio.run(test_full_m2m_flow())
