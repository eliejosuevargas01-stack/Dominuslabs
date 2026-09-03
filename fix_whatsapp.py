import re

file_path = "project-hub/backend/app/api/endpoints/whatsapp.py"
with open(file_path, "r") as f:
    content = f.read()

old_func = """    phone = payload.get("phone") or payload.get("number")
    message = payload.get("message") or payload.get("text")
    if not phone or not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Os campos 'phone' (ou 'number') e 'message' (ou 'text') são obrigatórios."
        )

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:messages:send")
    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers=headers,
        json_data={
            "phone": cleaned_phone,
            "number": cleaned_phone,
            "message": message,
            "text": message,
            "jid": f"{cleaned_phone}@s.whatsapp.net"
        },
        timeout=20.0
    )"""

new_func = """    phone = payload.get("phone") or payload.get("number") or payload.get("jid")
    message = payload.get("message") or payload.get("text") or ""
    media = payload.get("media")

    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O campo 'phone', 'number' ou 'jid' é obrigatório."
        )
        
    if not message and not media:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="É obrigatório enviar 'message' ou 'media'."
        )

    # Extrai só os digitos, mas preserva se o JID já vier no formato correto
    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    final_jid = phone if "@" in str(phone) else f"{cleaned_phone}@s.whatsapp.net"
    
    headers = await get_user_m2m_headers(current_user, db, scope="whatsapp:messages:send")
    
    json_data = {
        "phone": cleaned_phone,
        "number": cleaned_phone,
        "message": message,
        "text": message,
        "jid": final_jid
    }
    
    if media:
        json_data["media"] = media

    return await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers=headers,
        json_data=json_data,
        timeout=30.0 # Timeout aumentado por causa do envio de mídia
    )"""

content = content.replace(old_func, new_func)

with open(file_path, "w") as f:
    f.write(content)
print("Fix applied.")
