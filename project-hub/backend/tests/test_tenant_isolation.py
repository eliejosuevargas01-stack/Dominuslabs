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
    sig_inconsistent = hmac.new(settings.N8N_WEBHOOK_SECRET.encode(), raw_inconsistent, hashlib.sha256).hexdigest()
    h_inconsistent = {
        "Content-Type": "application/json",
        "X-Signature": sig_inconsistent,
        "X-Timestamp": str(int(time.time())),
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
    sig_own = hmac.new(settings.N8N_WEBHOOK_SECRET.encode(), raw_own, hashlib.sha256).hexdigest()
    h_own = {
        "Content-Type": "application/json",
        "X-Signature": sig_own,
        "X-Timestamp": str(int(time.time())),
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
