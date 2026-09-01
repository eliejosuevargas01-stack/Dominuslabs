import re

with open("project-hub/backend/app/api/endpoints/webhooks.py", "r") as f:
    content = f.read()

search_block = """    resolved_message_id = _event_text(
        message.get("message_id") or message.get("id") or key.get("id") or message_id
    )
    resolved_contact_id = _event_text(
        message.get("contact_jid")
        or message.get("contact_id")
        or message.get("chat_jid")
        or message.get("jid")
        or message.get("remoteJid")
        or key.get("remoteJid")
        or contact_id
        or lead_id
        or jid
        or phone
    )
    resolved_session_id = _event_session_id(
        message.get("session_id") or message.get("session") or message.get("whatsapp_instance") or session_id
    )
    resolved_tenant_id = _event_text(message.get("tenant_id") or message.get("tenant") or tenant_id)
    if not resolved_message_id:
        raise ValueError("message_id is required")
    if not resolved_contact_id:
        raise ValueError("contact_jid is required")
    if not resolved_session_id:
        raise ValueError("session_id is required")
    if not resolved_tenant_id:
        raise ValueError("tenant_id is required")

    from_me = _event_bool(
        message.get("is_from_me", message.get("from_me", message.get("fromMe", is_from_me or False)))
    )
    raw_sender = _event_text(message.get("sender") or sender).lower()
    normalized_sender = "user" if from_me or raw_sender in {"user", "me", "operator"} else "lead"
    message.update({"""

replace_block = """    resolved_message_id = _event_text(
        message.get("message_id") or message.get("id") or key.get("id") or message_id
    )

    from_me = _event_bool(
        message.get("is_from_me", message.get("from_me", message.get("fromMe", is_from_me or False)))
    )
    raw_sender = _event_text(message.get("sender") or sender).lower()
    normalized_sender = "user" if from_me or raw_sender in {"user", "me", "operator"} else "lead"

    if from_me or normalized_sender == "user":
        # For outbound, local JID is the sender, the remote contact is the recipient (to/remoteJid/participant).
        resolved_contact_id = _event_text(
            key.get("remoteJid")
            or message.get("participant")
            or message.get("to")
            or message.get("recipient")
            or message.get("contact_jid")
            or message.get("remoteJid")
            or message.get("jid")
            or contact_id
            or lead_id
            or jid
            or phone
        )
    else:
        # For inbound, local JID is the recipient, the remote contact is the sender.
        resolved_contact_id = _event_text(
            message.get("contact_jid")
            or message.get("contact_id")
            or message.get("chat_jid")
            or message.get("jid")
            or message.get("remoteJid")
            or key.get("remoteJid")
            or contact_id
            or lead_id
            or jid
            or phone
        )

    resolved_session_id = _event_session_id(
        message.get("session_id") or message.get("session") or message.get("whatsapp_instance") or session_id
    )
    resolved_tenant_id = _event_text(message.get("tenant_id") or message.get("tenant") or tenant_id)
    if not resolved_message_id:
        raise ValueError("message_id is required")
    if not resolved_contact_id:
        raise ValueError("contact_jid is required")
    if not resolved_session_id:
        raise ValueError("session_id is required")
    if not resolved_tenant_id:
        raise ValueError("tenant_id is required")

    message.update({"""

content = content.replace(search_block, replace_block)

with open("project-hub/backend/app/api/endpoints/webhooks.py", "w") as f:
    f.write(content)
