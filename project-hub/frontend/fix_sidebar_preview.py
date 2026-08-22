with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# Replace extractContent
old_extract = """            const extractContent = (m: any): string => {
              if (!m) return '';
              if (typeof m.content === 'string' && m.content.trim()) return m.content.trim();
              if (typeof m.message === 'string' && m.message.trim()) return m.message.trim();
              if (typeof m.text === 'string' && m.text.trim()) return m.text.trim();
              if (typeof m.body === 'string' && m.body.trim()) return m.body.trim();
              if (Array.isArray(m.messages) && m.messages.length > 0) return extractContent(m.messages[m.messages.length - 1]);
              if (Array.isArray(m.mensagens) && m.mensagens.length > 0) return extractContent(m.mensagens[m.mensagens.length - 1]);
              return '';
            };"""

new_extract = """            const extractContent = (m: any): string => {
              if (!m) return '';
              if (m._encrypted === true) return '';
              if (typeof m.content === 'string' && m.content.trim()) return m.content.trim();
              if (typeof m.message === 'string' && m.message.trim()) return m.message.trim();
              if (typeof m.text === 'string' && m.text.trim()) return m.text.trim();
              if (typeof m.body === 'string' && m.body.trim()) return m.body.trim();
              if (m.image_url) return '[imagem]';
              if (m.video_url) return '[vídeo]';
              if (m.audio_url) return '[áudio]';
              if (m.document_url) return '[documento]';
              if (Array.isArray(m.messages) && m.messages.length > 0) return extractContent(m.messages[m.messages.length - 1]);
              if (Array.isArray(m.mensagens) && m.mensagens.length > 0) return extractContent(m.mensagens[m.mensagens.length - 1]);
              return '';
            };"""
content = content.replace(old_extract, new_extract)

# Replace previewText calculation
old_preview_text = """            const latestMsg = newMsgs[newMsgs.length - 1];
            const previewText = extractContent(latestMsg) || 'Nova mensagem';"""

new_preview_text = """            const validMsgs = newMsgs.filter(m => extractContent(m) !== '');
            const latestMsg = validMsgs.length > 0 ? validMsgs[validMsgs.length - 1] : newMsgs[newMsgs.length - 1];
            const rawPreview = extractContent(latestMsg);"""
content = content.replace(old_preview_text, new_preview_text)

# Replace conv map return
old_conv_map = """                  return {
                    ...conv,
                    last_message_preview: previewText,
                    last_message_timestamp: msgTs,
                    unread_count: isCurrentlyOpenChat ? 0 : ((conv.unread_count || 0) + newMsgs.length),
                    participant_pushname: latestMsg.participant_pushname || conv.participant_pushname
                  };"""

new_conv_map = """                  return {
                    ...conv,
                    last_message_preview: rawPreview || conv.last_message_preview || 'Nova mensagem',
                    last_message_timestamp: msgTs,
                    unread_count: isCurrentlyOpenChat ? 0 : ((conv.unread_count || 0) + (rawPreview && !isFromMe ? 1 : 0)),
                    participant_pushname: latestMsg.participant_pushname || conv.participant_pushname
                  };"""
content = content.replace(old_conv_map, new_conv_map)

# Replace new conv fallback
old_new_conv = """                setConversations((prev) => [
                  {
                    contact_jid: parsed.contact_jid || parsed.chat_jid || parsed.lead_id || parsed.phone || notifiedJids[0],
                    session_id: parsed.session_id || 'default',
                    last_message_preview: previewText,
                    last_message_timestamp: msgTs,
                    unread_count: 1,
                    participant_pushname: latestMsg.participant_pushname
                  },
                  ...prev
                ]);"""

new_new_conv = """                setConversations((prev) => [
                  {
                    contact_jid: parsed.contact_jid || parsed.chat_jid || parsed.lead_id || parsed.phone || notifiedJids[0],
                    session_id: parsed.session_id || 'default',
                    last_message_preview: rawPreview || 'Nova mensagem',
                    last_message_timestamp: msgTs,
                    unread_count: (!isFromMe && rawPreview) ? 1 : 0,
                    participant_pushname: latestMsg.participant_pushname
                  },
                  ...prev
                ]);"""
content = content.replace(old_new_conv, new_new_conv)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
