from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import create_access_token
from datetime import datetime

client = TestClient(app)

def test_company_settings_crud(db):
    # 1. Generate auth header
    token = create_access_token({"sub": "admin@example.com"})
    headers = {"Authorization": f"Bearer {token}"}

    test_tenant = f"tenant_{int(datetime.utcnow().timestamp())}"

    # 2. Get initial settings (should auto-create default tenant settings)
    res = client.get(f"/api/v1/company-settings/?tenant_id={test_tenant}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["tenant_id"] == test_tenant
    assert data["company_name"] is None

    # 3. Update settings
    update_payload = {
        "company_name": "Dominus AI Tech",
        "cnpj_cpf": "12.345.678/0001-90",
        "phone": "+55 11 99999-8888",
        "email": "contato@dominus.ai",
        "address": "Av. Paulista, 1000 - São Paulo, SP",
        "business_hours": "Seg-Sex: 08:00 às 18:00",
        "tone_of_voice": "Consultivo e Especialista",
        "custom_instructions": "Sempre cumprimente chamando pelo nome e ofereça suporte proativo.",
        "exchange_policy": "Troca garantida em até 7 dias úteis sem custos.",
        "delivery_policy": "Entregas regionais em até 24h úteis.",
        "terms_of_service": "Termos de uso conforme a LGPD e normas vigentes.",
        "accepted_payment_types": ["Pix", "Cartão de Crédito", "Boleto"],
        "payment_notes": "Pix com 5% de desconto à vista.",
        "values_mission": "Inovação contínua e foco total no sucesso do cliente.",
        "menu_catalog": [
            {
                "id": "prod-1",
                "name": "Plano Pro Agente IA",
                "category": "Software",
                "price": 499.00,
                "description": "Atendimento automatizado WhatsApp e CRM",
                "available": True
            }
        ]
    }

    put_res = client.put(f"/api/v1/company-settings/?tenant_id={test_tenant}", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["company_name"] == "Dominus AI Tech"
    assert updated_data["tone_of_voice"] == "Consultivo e Especialista"
    assert len(updated_data["accepted_payment_types"]) == 3
    assert len(updated_data["menu_catalog"]) == 1
    assert updated_data["menu_catalog"][0]["name"] == "Plano Pro Agente IA"

    # 4. Get updated settings again
    get_res = client.get(f"/api/v1/company-settings/?tenant_id={test_tenant}", headers=headers)
    assert get_res.status_code == 200
    fetched_data = get_res.json()
    assert fetched_data["company_name"] == "Dominus AI Tech"
    assert fetched_data["email"] == "contato@dominus.ai"
