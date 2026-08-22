with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# 1. handleSendMessage fix
old_send = """    try {
      await sendOmnichannelMessage({
        contact_jid: selectedChat.contact_jid,
        session_id: targetSession,
        message: textToSend,
        phone: selectedChat.display_phone
      });

      setChatMessages(prev => prev.map(m => {
        if (m.message_id === tempMessage.message_id) {
          return { ...m, status: 'sent' };
        }
        return m;
      }));
    } catch (err) {"""

new_send = """    try {
      const res = await sendOmnichannelMessage({
        contact_jid: selectedChat.contact_jid,
        session_id: targetSession,
        message: textToSend,
        phone: selectedChat.display_phone
      });

      const realId = res.id || res.message_id || res.key?.id;
      if (realId) knownMessageIds.current.add(String(realId));

      setChatMessages(prev => prev.map(m => {
        if (m.message_id === tempMessage.message_id) {
          return { ...m, status: 'sent', message_id: realId || m.message_id, id: realId || m.id };
        }
        return m;
      }));
    } catch (err) {"""
content = content.replace(old_send, new_send)

# 2. sendMedia and audio recorder fixes
# Wait, let's see how media is sent!
