import re

file_path = "project-hub/backend/app/api/endpoints/webhooks.py"
with open(file_path, "r") as f:
    content = f.read()

old_block = """    session_id = payload.get("session_id", "default")
    phone = payload.get("phone") or payload.get("number") or payload.get("jid")
    message = payload.get("message") or payload.get("text")
    media = payload.get("media")
    
    if not phone:"""

new_block = """    session_id = payload.get("session_id", "default")
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
        
    if not phone:"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, "w") as f:
        f.write(content)
    print("webhooks.py base64_content support added.")
else:
    print("Could not find old block in webhooks.py")
