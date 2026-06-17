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

def test_project_rich_preview(client):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project_payload = {
        "name": "Super WhatsApp Project",
        "client_name": "VIP Client Name",
        "project_type": "Automação",
        "value": 2500.0,
        "status": "IN_PROGRESS"
    }
    create_res = client.post("/api/v1/projects/", json=project_payload, headers=headers)
    project_data = create_res.json()
    public_token = project_data["public_token"]

    res = client.get(f"/project/{public_token}")
    assert res.status_code == 200
    html = res.text
    
    assert "<title>Acompanhamento: Super WhatsApp Project</title>" in html
    assert 'meta property="og:title" content="Acompanhamento: Super WhatsApp Project"' in html
    assert 'meta property="og:description" content="Portal de acompanhamento do projeto Super WhatsApp Project (Automação) para o cliente VIP Client Name. Confira o status e progresso do desenvolvimento."' in html
    assert f'meta property="og:url" content="https://dominuslabs.online/project/{public_token}"' in html
    assert 'meta property="og:image" content="https://dominuslabs.online/logo.png"' in html

def test_project_feedback_and_showcase(client):
    # 1. Get auth token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create project
    project_payload = {
        "name": "Feedback Test Project",
        "client_name": "Reviewer Client",
        "project_type": "Landing Page",
        "value": 1200.0,
        "status": "IN_PROGRESS"
    }
    project_data = client.post("/api/v1/projects/", json=project_payload, headers=headers).json()
    project_id = project_data["id"]
    public_token = project_data["public_token"]

    # 3. Try submitting feedback while status is IN_PROGRESS (should fail with 400)
    feedback_payload = {
        "project_token": public_token,
        "final_result": "Muito bom",
        "service_rating": "Excelente",
        "invested_value_rating": "Justo",
        "process_rating": "Rápido",
        "improvements": "Nenhuma",
        "rating": 5
    }
    res = client.post("/api/v1/projects/public/feedback", json=feedback_payload)
    assert res.status_code == 400
    assert "Feedback só pode ser enviado para projetos concluídos." in res.json()["detail"]

    # 4. Set status to DELIVERED
    update_payload = {"status": "DELIVERED"}
    client.put(f"/api/v1/projects/{project_id}", json=update_payload, headers=headers)

    # 5. Submit feedback (should succeed)
    res = client.post("/api/v1/projects/public/feedback", json=feedback_payload)
    assert res.status_code == 201
    assert res.json()["status"] == "success"

    # 6. Submit duplicate feedback (should fail with 400)
    res = client.post("/api/v1/projects/public/feedback", json=feedback_payload)
    assert res.status_code == 400
    assert "Feedback já enviado para este projeto." in res.json()["detail"]

    # 7. Verify showcase data endpoint returns the correct projects and testimonial
    res = client.get("/api/v1/projects/public/showcase/data")
    assert res.status_code == 200
    data = res.json()
    assert "projects" in data
    assert "testimonials" in data
    
    # Showcase should contain the project
    target_proj = next((p for p in data["projects"] if p["name"] == "Feedback Test Project"), None)
    assert target_proj is not None
    assert target_proj["status"] == "DELIVERED"
    
    # Showcase should contain the testimonial
    target_testimonial = next((t for t in data["testimonials"] if t["client_name"] == "Reviewer Client"), None)
    assert target_testimonial is not None
    assert target_testimonial["rating"] == 5
    assert target_testimonial["comment"] == "Muito bom"

def test_viewer_role_permissions(client):
    # 1. Login as viewer
    res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.VIEWER_USERNAME, "password": settings.VIEWER_PASSWORD}
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify reading projects works
    res = client.get("/api/v1/projects/", headers=headers)
    assert res.status_code == 200

    # 3. Verify creating a project succeeds for viewer
    project_payload = {
        "name": "Viewer Try Project",
        "client_name": "Viewer Client",
        "project_type": "Landing Page",
        "value": 1200.0,
        "status": "IN_PROGRESS"
    }
    res = client.post("/api/v1/projects/", json=project_payload, headers=headers)
    assert res.status_code == 200

    # 4. Verify editing/updating a project fails with 403
    res = client.put("/api/v1/projects/1", json={"name": "Hacked"}, headers=headers)
    assert res.status_code == 403

    # 5. Verify creating a task fails with 403
    res = client.post("/api/v1/projects/1/tasks", json={"name": "Hacked Task"}, headers=headers)
    assert res.status_code == 403

    # 6. Verify updating a task status fails with 403
    res = client.put("/api/v1/projects/tasks/1", json={"status": "DONE"}, headers=headers)
    assert res.status_code == 403

    # 7. Verify uploading a file/asset fails with 403
    upload_payload = {"project_id": 1}
    files = {"file": ("test.txt", b"hello content", "text/plain")}
    res = client.post("/api/v1/uploads/", data=upload_payload, files=files, headers=headers)
    assert res.status_code == 403

def test_delete_project_permissions(client):
    # 1. Login as Admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create a project to delete
    project_payload = {
        "name": "Delete Test Project",
        "client_name": "Delete Client",
        "project_type": "Landing Page",
        "value": 1200.0,
        "status": "NEW"
    }
    create_res = client.post("/api/v1/projects/", json=project_payload, headers=admin_headers)
    assert create_res.status_code == 200
    project_id = create_res.json()["id"]

    # 3. Login as Viewer (custom role, not admin)
    viewer_login = client.post(
        "/api/v1/auth/login",
        json={"username": settings.VIEWER_USERNAME, "password": settings.VIEWER_PASSWORD}
    )
    viewer_token = viewer_login.json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # 4. Attempt to delete project as Viewer (should fail with 403)
    delete_viewer_res = client.delete(f"/api/v1/projects/{project_id}", headers=viewer_headers)
    assert delete_viewer_res.status_code == 403

    # 5. Delete project as Admin (should succeed with 200)
    delete_admin_res = client.delete(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert delete_admin_res.status_code == 200
    assert delete_admin_res.json()["status"] == "success"

    # 6. Verify project is deleted (should return 404)
    get_res = client.get(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert get_res.status_code == 404

