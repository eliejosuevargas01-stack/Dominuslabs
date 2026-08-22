with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_load = """          if (!preview) {
            const msgs = Array.isArray(item.messages) ? item.messages : (Array.isArray(item.mensagens) ? item.mensagens : []);
            if (msgs.length > 0) {
              const lastM = msgs[msgs.length - 1];
              preview = lastM.content || lastM.message || lastM.text || lastM.body || '';
            }
          }
          return {
            ...item,
            contact_jid: jid,
            push_name: resolvedName,
            display_phone: item.display_phone || null,
            profile_pic_url: item.profile_pic_url || '',
            last_message_preview: preview,
            last_message_timestamp: item.last_message_timestamp || new Date().toISOString()
          };"""

new_load = """          let is_from_me = item.last_message_is_from_me;
          let status = item.last_message_status || item.status || 'sent';
          if (!preview) {
            const msgs = Array.isArray(item.messages) ? item.messages : (Array.isArray(item.mensagens) ? item.mensagens : []);
            if (msgs.length > 0) {
              const lastM = msgs[msgs.length - 1];
              preview = lastM.content || lastM.message || lastM.text || lastM.body || '';
              if (is_from_me === undefined) is_from_me = lastM.isFromMe || lastM.is_from_me || lastM.fromMe;
              if (lastM.status) status = lastM.status;
            }
          }
          return {
            ...item,
            contact_jid: jid,
            push_name: resolvedName,
            display_phone: item.display_phone || null,
            profile_pic_url: item.profile_pic_url || '',
            last_message_preview: preview,
            last_message_is_from_me: is_from_me,
            last_message_status: status,
            last_message_timestamp: item.last_message_timestamp || new Date().toISOString()
          };"""

content = content.replace(old_load, new_load)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
