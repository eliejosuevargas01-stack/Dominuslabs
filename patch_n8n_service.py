import re

with open("project-hub/backend/app/services/n8n_service.py", "r") as f:
    content = f.read()

search_block = """        outgoing_payload = {
            "action": "send_message",
            "jid": cleaned_phone,
            "text": message_text,
            "number": cleaned_phone,
            "body": message_text,
            "phone": phone,
            "message": message_text,
            "lead_id": lead_id,
            "contact_jid": contact_jid,
        }"""

replace_block = """        outgoing_payload = {
            "action": "send_message",
            "jid": cleaned_phone,
            "text": message_text,
            "number": cleaned_phone,
            "body": message_text,
            "phone": phone,
            "message": message_text,
            "lead_id": lead_id,
            "contact_jid": contact_jid,
            "is_from_me": True,
            "sender": "user",
        }"""

content = content.replace(search_block, replace_block)

with open("project-hub/backend/app/services/n8n_service.py", "w") as f:
    f.write(content)
