file_path = "project-hub/backend/app/api/endpoints/webhooks.py"
with open(file_path, "r") as f:
    content = f.read()

start_marker = "async def n8n_outbound_whatsapp_send("
start_idx = content.find(start_marker)

new_func = """async def n8n_outbound_whatsapp_send(
    payload: Dict[str, Any] = Body(...),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db)
):
    master_key = x_master_api_key or payload.get("master_api_key") or payload.get("x_master_api_key")
    if not master_key or master_key != settings.WHATSAPP_MASTER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")

    session_id = payload.get("session_id", "default")
    phone = payload.get("phone") or payload.get("number") or payload.get("jid") or payload.get("contact_jid")
    message = payload.get("message") or payload.get("text")
    media = payload.get("media")
    base64_content = payload.get("base64_content")
    
    if base64_content and not media:
        media = {
            "data": base64_content,
            "mimeType": payload.get("mimeType") or "application/pdf",
            "fileName": payload.get("fileName") or "documento.pdf",
            "kind": payload.get("kind") or "document"
        }

    if not phone:
        raise HTTPException(status_code=400, detail="Missing phone, number or jid")

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    final_jid = phone if "@" in str(phone) else f"{cleaned_phone}@s.whatsapp.net"
    
    from app.api.endpoints.whatsapp import make_whatsapp_api_request
    from app.services.identity_service import get_m2m_jwt
    
    tenant_id = payload.get("tenant_id") or getattr(settings, "ADMIN_TENANT_ID", "admin") or "admin"
    jwt_token = await get_m2m_jwt(tenant_id=tenant_id, scope="whatsapp:messages:send")
    
    headers = {
        "X-Master-API-Key": settings.WHATSAPP_MASTER_SECRET,
        "x-tenant-id": tenant_id,
        "x-session-token": jwt_token,
        "Authorization": f"Bearer {jwt_token}"
    }
    
    json_data = {
        "phone": cleaned_phone,
        "number": cleaned_phone,
        "jid": final_jid
    }
    if message:
        json_data["message"] = message
        json_data["text"] = message
    if media:
        json_data["media"] = media
        
    for k, v in payload.items():
        if k not in ["phone", "number", "message", "text", "session_id", "tenant_id", "jid", "contact_jid", "master_api_key", "x_master_api_key", "base64_content", "media", "mimeType", "fileName", "kind"]:
            json_data[k] = v

    res = await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers=headers,
        json_data=json_data,
        timeout=30.0
    )
    
    return JSONResponse(status_code=200, content=res)
"""

content = content[:start_idx] + new_func
with open(file_path, "w") as f:
    f.write(content)
print("webhooks.py fixed successfully!")
