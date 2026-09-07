import pytest
from app.core.auth import create_access_token
from app.models.user import User
from app.core.config import settings

def test_company_settings_tenant_isolation(client, db):
    # 1. Create User A in Tenant A
    user_a = User(
        email="user_a@tenant-a.com",
        hashed_password="hash_password_a",
        tenant_id="tenant_a",
        role="custom",
        permissions="read,write,update,delete"
    )
    db.add(user_a)

    # 2. Create User B in Tenant B
    user_b = User(
        email="user_b@tenant-b.com",
        hashed_password="hash_password_b",
        tenant_id="tenant_b",
        role="custom",
        permissions="read,write,update,delete"
    )
    db.add(user_b)
    db.commit()

    token_a = create_access_token({"sub": user_a.email, "tenant_id": user_a.tenant_id, "role": user_a.role})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    token_b = create_access_token({"sub": user_b.email, "tenant_id": user_b.tenant_id, "role": user_b.role})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A updates Tenant A settings
    payload_a = {
        "company_name": "Company Alpha",
        "cnpj_cpf": "11.111.111/0001-11",
        "phone": "+55 11 1111-1111",
        "email": "alpha@tenant-a.com",
        "address": "Rua Alpha, 1",
        "accepted_payment_types": ["Pix"],
        "menu_catalog": []
    }
    res = client.put("/api/v1/company-settings/", json=payload_a, headers=headers_a)
    assert res.status_code == 200
    assert res.json()["company_name"] == "Company Alpha"
    assert res.json()["tenant_id"] == "tenant_a"

    # User B updates Tenant B settings
    payload_b = {
        "company_name": "Company Beta",
        "cnpj_cpf": "22.222.222/0002-22",
        "phone": "+55 11 2222-2222",
        "email": "beta@tenant-b.com",
        "address": "Rua Beta, 2",
        "accepted_payment_types": ["Cartão de Crédito"],
        "menu_catalog": []
    }
    res = client.put("/api/v1/company-settings/", json=payload_b, headers=headers_b)
    assert res.status_code == 200
    assert res.json()["company_name"] == "Company Beta"
    assert res.json()["tenant_id"] == "tenant_b"

    # User A reads settings -> gets Alpha
    res = client.get("/api/v1/company-settings/", headers=headers_a)
    assert res.status_code == 200
    assert res.json()["company_name"] == "Company Alpha"
    assert res.json()["tenant_id"] == "tenant_a"

    # User B reads settings -> gets Beta
    res = client.get("/api/v1/company-settings/", headers=headers_b)
    assert res.status_code == 200
    assert res.json()["company_name"] == "Company Beta"
    assert res.json()["tenant_id"] == "tenant_b"

    # User B attempts to query tenant_a via query param -> IGNORED, still returns Beta
    res = client.get("/api/v1/company-settings/?tenant_id=tenant_a", headers=headers_b)
    assert res.status_code == 200
    assert res.json()["company_name"] == "Company Beta"
    assert res.json()["tenant_id"] == "tenant_b"

    # User B attempts to update tenant_a via query param -> IGNORED, still modifies Beta
    malicious_payload = {
        "company_name": "Hacked Alpha",
        "cnpj_cpf": "99.999.999/0001-99",
        "phone": "+55 11 9999-9999",
        "email": "hacker@tenant-b.com",
        "address": "Rua Hacker, 99",
        "accepted_payment_types": ["Pix"],
        "menu_catalog": []
    }
    res = client.put("/api/v1/company-settings/?tenant_id=tenant_a", json=malicious_payload, headers=headers_b)
    assert res.status_code == 200
    assert res.json()["company_name"] == "Hacked Alpha"
    assert res.json()["tenant_id"] == "tenant_b"

    # Verify User A settings are completely uncorrupted
    res = client.get("/api/v1/company-settings/", headers=headers_a)
    assert res.status_code == 200
    assert res.json()["company_name"] == "Company Alpha"
    assert res.json()["tenant_id"] == "tenant_a"


def test_webhook_cross_tenant_rejection(client, db):
    import hmac, hashlib, json, time

    user_b = User(
        email="operator_b@tenant-b.com",
        hashed_password="hash_password_b",
        tenant_id="tenant_b",
        role="custom",
        permissions="read,write"
    )
    db.add(user_b)
    db.commit()

    token_b = create_access_token({"sub": user_b.email, "tenant_id": user_b.tenant_id, "role": user_b.role})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Human JWT is rejected on n8n webhook with 403 Forbidden
    cross_tenant_msg = [{
        "message_id": "msg-999",
        "contact_jid": "5511999998888@s.whatsapp.net",
        "session_id": "sess-tenant-a",
        "tenant_id": "tenant_a",
        "fromMe": False,
        "text": "Malicious cross-tenant injection"
    }]

    res = client.post("/api/v1/webhooks/crm/update-chat", json=cross_tenant_msg, headers=headers_b)
    assert res.status_code == 403
    assert "Webhooks n8n aceitam exclusivamente identidade de serviço" in res.json()["detail"]

    # 2. Batch with inconsistent tenants is rejected with 400 Bad Request
    inconsistent_batch = [
        {
            "message_id": "msg-1",
            "contact_jid": "5511999998888@s.whatsapp.net",
            "session_id": "sess-tenant-a",
            "tenant_id": "tenant_a",
            "fromMe": False,
            "text": "Tenant A msg"
        },
        {
            "message_id": "msg-2",
            "contact_jid": "5511999998888@s.whatsapp.net",
            "session_id": "sess-tenant-b",
            "tenant_id": "tenant_b",
            "fromMe": False,
            "text": "Tenant B msg"
        }
    ]
    raw_inconsistent = json.dumps(inconsistent_batch).encode()
    ts_inconsistent = str(int(time.time()))
    eid_inconsistent = "evt-inconsistent-1"
    sig_inconsistent = hmac.new(
        settings.N8N_WEBHOOK_SECRET.encode(),
        f"{ts_inconsistent}.{eid_inconsistent}.".encode() + raw_inconsistent,
        hashlib.sha256
    ).hexdigest()
    h_inconsistent = {
        "Content-Type": "application/json",
        "X-Signature": sig_inconsistent,
        "X-Timestamp": ts_inconsistent,
        "X-Event-Id": eid_inconsistent,
    }
    res = client.post("/api/v1/webhooks/crm/update-chat", content=raw_inconsistent, headers=h_inconsistent)
    assert res.status_code == 400
    assert "Inconsistência de tenant" in res.json()["detail"]

    # 3. Legitimate single-tenant message with valid HMAC succeeds
    own_tenant_msg = [{
        "message_id": "msg-1000",
        "contact_jid": "5511999998888@s.whatsapp.net",
        "session_id": "sess-tenant-b",
        "tenant_id": "tenant_b",
        "fromMe": False,
        "text": "Legitimate tenant message"
    }]
    raw_own = json.dumps(own_tenant_msg).encode()
    ts_own = str(int(time.time()))
    eid_own = "evt-own-1"
    sig_own = hmac.new(
        settings.N8N_WEBHOOK_SECRET.encode(),
        f"{ts_own}.{eid_own}.".encode() + raw_own,
        hashlib.sha256
    ).hexdigest()
    h_own = {
        "Content-Type": "application/json",
        "X-Signature": sig_own,
        "X-Timestamp": ts_own,
        "X-Event-Id": eid_own,
    }
    res = client.post("/api/v1/webhooks/crm/update-chat", content=raw_own, headers=h_own)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["tenant_id"] == "tenant_b"


def test_unauthenticated_request_never_impersonates_admin(client):
    # Missing auth
    res = client.get("/api/v1/company-settings/")
    assert res.status_code in (401, 403)

    # Invalid token
    res = client.get("/api/v1/company-settings/", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_crm_leads_cache_multi_tenant_isolation():
    """Valida que o cache de leads do n8n_service isola estritamente os tenants."""
    from unittest.mock import patch, AsyncMock
    import httpx
    from app.services.n8n_service import N8NService
    from app.core.crypto import encrypt_payload

    N8NService._leads_cache.clear()

    async def fake_post(url, **kwargs):
        # Descriptografa body para descobrir o tenant_id da requisição
        body = kwargs.get("json", {})
        from app.core.crypto import decrypt_payload
        dec = decrypt_payload(body) if isinstance(body, dict) and body.get("_encrypted") else body
        t_id = dec.get("tenant_id") if isinstance(dec, dict) else None

        if t_id == "tenant_alpha":
            raw = [{"id": "lead_alpha_1", "empresa_nome": "Alpha Corp", "status": "Prospectado"}]
        else:
            raw = [{"id": "lead_beta_1", "empresa_nome": "Beta Corp", "status": "Qualificado"}]

        enc_resp = encrypt_payload(raw, target="dominus")
        return httpx.Response(200, json=enc_resp, request=httpx.Request("POST", url))

    mock_client = AsyncMock()
    mock_client.post = fake_post

    with patch("httpx.AsyncClient") as mock_async_client_cls:
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        # 1. Tenant Alpha busca leads
        leads_alpha = await N8NService.get_leads(user_id="user_a", tenant_id="tenant_alpha")
        assert len(leads_alpha) > 0
        assert leads_alpha[0]["id"] == "lead_alpha_1"

        # 2. Tenant Beta busca leads
        leads_beta = await N8NService.get_leads(user_id="user_b", tenant_id="tenant_beta")
        assert len(leads_beta) > 0
        assert leads_beta[0]["id"] == "lead_beta_1"

        # 3. Verifica que os caches em memória estão particionados por tenant
        assert "tenant_alpha" in N8NService._leads_cache
        assert "tenant_beta" in N8NService._leads_cache
        assert N8NService._leads_cache["tenant_alpha"]["data"][0]["id"] == "lead_alpha_1"
        assert N8NService._leads_cache["tenant_beta"]["data"][0]["id"] == "lead_beta_1"

        # 4. Invalidação direcionada ao tenant_alpha NÃO afeta tenant_beta
        N8NService.invalidate_leads_cache(tenant_id="tenant_alpha")
        assert "tenant_alpha" not in N8NService._leads_cache
        assert "tenant_beta" in N8NService._leads_cache

        # 5. Tentativa de buscar leads sem tenant_id deve falhar fail-closed com ValueError
        with pytest.raises(ValueError) as exc_val:
            await N8NService.get_leads(user_id="user_anonymous", tenant_id=None)
        assert "tenant_id é obrigatório" in str(exc_val.value)


@pytest.mark.anyio
async def test_sse_lead_events_multi_tenant_isolation():
    """Valida que SSE lead_listeners não vazam eventos cross-tenant."""
    import asyncio
    from app.api.endpoints.webhooks import lead_listeners, notify_lead_listeners

    lead_listeners.clear()

    q_alpha = asyncio.Queue()
    q_beta = asyncio.Queue()

    # Registra listeners para o mesmo lead_id mas em tenants distintos
    lead_listeners[("tenant_alpha", "lead_same_id")] = [("user_alpha@test.com", q_alpha)]
    lead_listeners[("tenant_beta", "lead_same_id")] = [("user_beta@test.com", q_beta)]

    # Dispara reload para tenant_alpha
    await notify_lead_listeners("lead_same_id", tenant_id="tenant_alpha", event="reload")

    # Tenant Alpha deve receber o evento
    assert not q_alpha.empty()
    assert await q_alpha.get() == "reload"

    # Tenant Beta NUNCA deve receber o evento
    assert q_beta.empty()

    # Disparo sem tenant_id é descartado sumariamente (fail-closed)
    await notify_lead_listeners("lead_same_id", tenant_id=None, event="reload")
    assert q_alpha.empty()
    assert q_beta.empty()


@pytest.mark.anyio
async def test_crm_messages_and_inbound_isolation_between_tenants(monkeypatch):
    """Valida que mensagens recebidas via inbound webhook e recuperadas pelo n8n_service não vazam entre tenants com o mesmo lead_id."""
    from app.services.n8n_service import (
        N8NService,
        MOCK_CONVERSATIONS,
        MOCK_ACTIVITIES,
        RAW_LEADS_CACHE
    )
    from app.core.config import settings

    monkeypatch.setattr(settings, "CRM_GET_MESSAGES_WEBHOOK_URL", None)
    monkeypatch.setattr(settings, "CRM_UPDATE_LEAD_WEBHOOK_URL", None)

    lead_id = "shared_lead_xyz"
    tenant_a = "tenant_alpha_crm"
    tenant_b = "tenant_beta_crm"

    # Limpa caches relevantes
    MOCK_CONVERSATIONS.pop(f"{tenant_a}:{lead_id}", None)
    MOCK_CONVERSATIONS.pop(f"{tenant_b}:{lead_id}", None)
    MOCK_CONVERSATIONS.pop(lead_id, None)
    MOCK_ACTIVITIES.pop(f"{tenant_a}:{lead_id}", None)
    MOCK_ACTIVITIES.pop(f"{tenant_b}:{lead_id}", None)
    MOCK_ACTIVITIES.pop(lead_id, None)

    # 1. Simula inbound message recebida para Tenant A
    key_a = f"{tenant_a}:{lead_id}"
    MOCK_CONVERSATIONS[key_a] = [{
        "id": "msg_alpha_1",
        "sender": "lead",
        "message": "Mensagem privada do Tenant Alpha",
        "channel": "whatsapp",
        "timestamp": "2026-09-06T20:00:00Z"
    }]

    # 2. Tenant A consulta histórico -> encontra a mensagem
    msgs_a = await N8NService.get_messages(lead_id, tenant_id=tenant_a)
    assert len(msgs_a) == 1
    assert msgs_a[0]["message"] == "Mensagem privada do Tenant Alpha"

    # 3. Tenant B consulta histórico do mesmo lead_id -> lista vazia, isolamento estrito
    msgs_b = await N8NService.get_messages(lead_id, tenant_id=tenant_b)
    assert len(msgs_b) == 0

    # 4. Atividades criadas no Tenant A não vazam para Tenant B
    await N8NService.create_activity(lead_id, "stage_change", {"stage": "proposta"}, tenant_id=tenant_a)
    acts_a = await N8NService.get_activities(lead_id, tenant_id=tenant_a)
    acts_b = await N8NService.get_activities(lead_id, tenant_id=tenant_b)
    assert len(acts_a) == 1
    assert acts_a[0]["event_type"] == "stage_change"
    assert len(acts_b) == 0

    # 5. Deleção no Tenant A limpa o cache de A sem afetar B
    await N8NService.delete_lead(lead_id, tenant_id=tenant_a)
    assert f"{tenant_a}:{lead_id}" not in MOCK_CONVERSATIONS
    assert f"{tenant_a}:{lead_id}" not in MOCK_ACTIVITIES



