file_path = "project-hub/backend/app/api/endpoints/webhooks.py"
with open(file_path, "r") as f:
    content = f.read()

start_marker = "    session_id = payload.get(\"session_id\", \"default\")"
end_marker = "    )"

start_idx = content.find(start_marker)
if start_idx == -1:
    print("Start marker not found")
else:
    end_idx = content.find(end_marker, start_idx) + len(end_marker)
    
    new_func = """    session_id = payload.get("session_id", "default")
    phone = payload.get("phone") or payload.get("number") or payload.get("jid")
    message = payload.get("message") or payload.get("text")
    media = payload.get("media")
    
    if not phone:
        raise HTTPException(status_code=400, detail="Missing phone, number or jid")
        
    if not message and not media:
        raise HTTPException(status_code=400, detail="Missing message or media")

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

    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers=headers,
        json_data=json_data,
        timeout=30.0
    )"""

    # We need to make sure we replace up to the LAST character of the make_whatsapp_api_request call
    end_marker_real = "timeout=15.0\n    )"
    end_idx_real = content.find(end_marker_real, start_idx)
    if end_idx_real != -1:
        end_idx_real += len(end_marker_real)
        content = content[:start_idx] + new_func + content[end_idx_real:]
        
        with open(file_path, "w") as f:
            f.write(content)
        print("Webhooks fixed finally.")
    else:
        print("End marker not found")
