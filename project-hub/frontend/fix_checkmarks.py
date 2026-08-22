import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# 1. Fix the chat bubble checkmark (delivery_ack)
old_bubble_check = "if (st === 'received' || st === 'delivered') {"
new_bubble_check = "if (st === 'received' || st === 'delivered' || st === 'delivery_ack') {"
content = content.replace(old_bubble_check, new_bubble_check)

# 2. Fix the message UPDATE in setChatMessages (CONDITIONAL 1)
old_set_chat = """              for (const m of newMsgs) {
                if (!m) continue;
                const id = String(m.message_id || m.id || m.key?.id || '');
                if (id && !existingIds.has(id)) {
                  existingIds.add(id);
                  msgsToAdd.push(m);
                } else if (!id) {
                  msgsToAdd.push(m);
                }
              }

              if (msgsToAdd.length === 0) return prevMsgs;
              return [...prevMsgs, ...msgsToAdd];"""

new_set_chat = """              let updatedMsgs = [...prevMsgs];
              for (const m of newMsgs) {
                if (!m) continue;
                const id = String(m.message_id || m.id || m.key?.id || '');
                if (id && existingIds.has(id)) {
                  updatedMsgs = updatedMsgs.map(oldM => {
                     const oldId = String(oldM.message_id || oldM.id || oldM.key?.id || '');
                     if (oldId === id) {
                        return { ...oldM, ...m, status: m.status || oldM.status };
                     }
                     return oldM;
                  });
                } else {
                  if (id) existingIds.add(id);
                  msgsToAdd.push(m);
                }
              }

              if (msgsToAdd.length === 0) return updatedMsgs;
              return [...updatedMsgs, ...msgsToAdd];"""
content = content.replace(old_set_chat, new_set_chat)

# 3. Fix the setConversations logic inside CONDITIONAL 2
old_conv_map = """                  return {
                    ...conv,
                    last_message_preview: rawPreview || conv.last_message_preview || 'Nova mensagem',
                    last_message_timestamp: msgTs,
                    unread_count: isCurrentlyOpenChat ? 0 : ((conv.unread_count || 0) + (rawPreview && !isFromMe ? 1 : 0)),
                    participant_pushname: latestMsg.participant_pushname || conv.participant_pushname
                  };"""

new_conv_map = """                  return {
                    ...conv,
                    last_message_preview: rawPreview || conv.last_message_preview || 'Nova mensagem',
                    last_message_timestamp: msgTs,
                    unread_count: isCurrentlyOpenChat ? 0 : ((conv.unread_count || 0) + (rawPreview && !isFromMe ? 1 : 0)),
                    participant_pushname: latestMsg.participant_pushname || conv.participant_pushname,
                    last_message_is_from_me: rawPreview ? isFromMe : conv.last_message_is_from_me,
                    last_message_status: (latestMsg.status || (rawPreview ? 'sent' : conv.last_message_status))
                  };"""
content = content.replace(old_conv_map, new_conv_map)

# 4. Fix sendOmnichannelMessage updating local conversation
old_send_update = """          ...c,
          last_message_preview: textToSend,
          last_message_timestamp: new Date().toISOString()
        };"""

new_send_update = """          ...c,
          last_message_preview: textToSend,
          last_message_timestamp: new Date().toISOString(),
          last_message_is_from_me: true,
          last_message_status: 'sending'
        };"""
content = content.replace(old_send_update, new_send_update)

# 5. Fix sendOmnichannelMedia updating local conversation
old_media_send_update = """          ...c,
          last_message_preview: `[${selectedMediaType}]`,
          last_message_timestamp: new Date().toISOString()
        };"""

new_media_send_update = """          ...c,
          last_message_preview: `[${selectedMediaType}]`,
          last_message_timestamp: new Date().toISOString(),
          last_message_is_from_me: true,
          last_message_status: 'sending'
        };"""
content = content.replace(old_media_send_update, new_media_send_update)

# 6. Render the checkmark in the sidebar
old_sidebar_preview = """                            {item.last_message_preview || 'Nova conversa'}
                          </span>"""

new_sidebar_preview = """                            {item.last_message_is_from_me && (
                              <span className="inline-flex mr-1 align-middle">
                                {(item.last_message_status === 'read' || item.last_message_status === 'played') ? (
                                  <CheckCheck className="w-3.5 h-3.5 text-sky-500" />
                                ) : (item.last_message_status === 'received' || item.last_message_status === 'delivered' || item.last_message_status === 'delivery_ack') ? (
                                  <CheckCheck className="w-3.5 h-3.5 text-slate-400" />
                                ) : (item.last_message_status === 'sending') ? (
                                  <Clock className="w-3 h-3 text-slate-400 animate-pulse" />
                                ) : (
                                  <Check className="w-3.5 h-3.5 text-slate-400" />
                                )}
                              </span>
                            )}
                            {item.last_message_preview || 'Nova conversa'}
                          </span>"""
content = content.replace(old_sidebar_preview, new_sidebar_preview)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
