from app.core.config import settings

def test_login(client):
    # Test valid login
    response = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test invalid login
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "wrong", "password": "wrong"}
    )
    assert response.status_code == 401

def test_create_and_read_project(client):
    # Get auth token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test unauthorized listing
    res = client.get("/api/v1/projects/")
    assert res.status_code == 401

    # Test authorized listing (empty)
    res = client.get("/api/v1/projects/", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 0

    # Test create project
    project_payload = {
        "name": "Test Project",
        "client_name": "Test Client",
        "description": "Project for unit testing",
        "project_type": "Landing Page",
        "value": 1500.0,
        "status": "NEW"
    }
    res = client.post("/api/v1/projects/", json=project_payload, headers=headers)
    assert res.status_code == 200
    project_data = res.json()
    assert project_data["name"] == "Test Project"
    assert "public_token" in project_data
    project_id = project_data["id"]

    # Test get project details
    res = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["client_name"] == "Test Client"

    # Test update project
    update_payload = {"name": "Updated Test Project"}
    res = client.put(f"/api/v1/projects/{project_id}", json=update_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Test Project"

def test_public_project(client):
    # Get auth token and create project
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project_payload = {
        "name": "Public Project",
        "client_name": "Public Client",
        "project_type": "E-Commerce",
        "value": 3000.0,
        "status": "IN_PROGRESS"
    }
    create_res = client.post("/api/v1/projects/", json=project_payload, headers=headers)
    project_data = create_res.json()
    public_token = project_data["public_token"]

    # Test accessing public project without headers
    res = client.get(f"/api/v1/projects/public/{public_token}")
    assert res.status_code == 200
    data = res.json()
    assert "project" in data
    assert data["project"]["name"] == "Public Project"
    assert "progress" in data
    assert data["progress"] == 0.0

def test_webhook_processing(client):
    # Get auth token and create project
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    project_payload = {
        "name": "Webhook Project",
        "client_name": "Webhook Client",
        "project_type": "Landing Page",
        "value": 1000.0,
        "status": "IN_PROGRESS"
    }
    project_data = client.post("/api/v1/projects/", json=project_payload, headers=headers).json()
    project_id = project_data["id"]
    public_token = project_data["public_token"]

    # 2. Add a task to this project
    task_payload = {
        "project_id": project_id,
        "name": "GitHub Task Fix",
        "description": "This task should be completed by github commit webhook"
    }
    task_data = client.post(f"/api/v1/projects/{project_id}/tasks", json=task_payload, headers=headers).json()
    task_id = task_data["id"]

    # 3. Simulate GitHub Push Webhook
    webhook_payload = {
        "commits": [
            {
                "id": "abc123hash",
                "message": "feat: completed task GitHub Task Fix",
                "author": {"name": "Test Developer"},
                "timestamp": "2026-06-10T12:00:00Z"
            }
        ]
    }
    res = client.post(f"/api/v1/webhooks/github/{public_token}", json=webhook_payload)
    assert res.status_code == 200
    
    # 4. Verify task was marked as completed and commit was logged
    tasks_res = client.get(f"/api/v1/projects/{project_id}/tasks", headers=headers)
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()
    target_task = next((t for t in tasks if t["id"] == task_id), None)
    assert target_task is not None
    assert target_task["status"] == "DONE"
    
    # Verify commit log
    commits_res = client.get(f"/api/v1/projects/{project_id}/commits", headers=headers)
    assert commits_res.status_code == 200
    commits = commits_res.json()
    assert len(commits) == 1
    assert commits[0]["commit_hash"] == "abc123hash"
