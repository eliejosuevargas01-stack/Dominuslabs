from app.core.config import settings

def test_crm_endpoints(client):
    # Get auth token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test unauthorized listing
    res = client.get("/api/v1/crm/leads")
    assert res.status_code == 401

    # Test authorized listing
    res = client.get("/api/v1/crm/leads", headers=headers)
    assert res.status_code == 200
    leads = res.json()
    assert len(leads) > 0
    first_lead = leads[0]
    assert "company_name" in first_lead
    assert "status" in first_lead
    lead_id = first_lead["id"]

    # Test updating a lead
    update_payload = {
        "company_name": "Clínica Sorriso Atualizada",
        "notes": "Nova nota de teste",
        "status": "NEGOTIATING"
    }
    res = client.put(f"/api/v1/crm/leads/{lead_id}", json=update_payload, headers=headers)
    assert res.status_code == 200
    updated_lead = res.json()
    assert updated_lead["company_name"] == "Clínica Sorriso Atualizada"
    assert updated_lead["status"] == "NEGOTIATING"

    # Test get conversation messages
    res = client.get(f"/api/v1/crm/conversations/{lead_id}", headers=headers)
    assert res.status_code == 200
    messages = res.json()
    assert isinstance(messages, list)

    # Test send whatsapp message
    send_payload = {
        "lead_id": lead_id,
        "phone": "+5511999999991",
        "message": "Olá, esta é uma mensagem de teste!"
    }
    res = client.post("/api/v1/crm/messages/send", json=send_payload, headers=headers)
    assert res.status_code == 200
    msg_sent = res.json()
    assert msg_sent["sender"] == "user"
    assert msg_sent["message"] == "Olá, esta é uma mensagem de teste!"

    # Test get dashboard metrics
    res = client.get("/api/v1/crm/dashboard", headers=headers)
    assert res.status_code == 200
    metrics = res.json()
    assert "total_leads" in metrics
    assert "taxa_conversao" in metrics

    # Test activities timeline
    res = client.get(f"/api/v1/crm/leads/{lead_id}/activities", headers=headers)
    assert res.status_code == 200
    activities = res.json()
    assert isinstance(activities, list)

    # Test create activity
    activity_payload = {
        "event_type": "proposal_opened",
        "metadata": {"amount": 1200}
    }
    res = client.post(f"/api/v1/crm/leads/{lead_id}/activities", json=activity_payload, headers=headers)
    assert res.status_code == 200
    activity_created = res.json()
    assert activity_created["event_type"] == "proposal_opened"
    assert activity_created["lead_id"] == lead_id

def test_scrapper_endpoints(client):
    # Get auth token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test unauthorized scrapper run
    res = client.post("/api/v1/scrapper/run", json={
        "queries": ["Clínicas odontológicas São Paulo"],
        "platforms": ["Google Maps"],
        "min_results": 5,
        "max_results": 20
    })
    assert res.status_code == 401

    # Test authorized scrapper run
    res = client.post("/api/v1/scrapper/run", json={
        "queries": ["Clínicas odontológicas São Paulo"],
        "platforms": ["Google Maps"],
        "min_results": 5,
        "max_results": 20
    }, headers=headers)
    assert res.status_code == 200
    scrapper_result = res.json()
    assert scrapper_result["status"] == "success"
