with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_parsing = """          if (event.data.startsWith('{')) {
            const parsed = JSON.parse(event.data);
            if (Array.isArray(parsed.messages) && parsed.messages.length > 0) {
              newMsgs = parsed.messages;
            } else if (parsed.message && typeof parsed.message === 'object') {
              newMsgs = [parsed.message];
            }"""

new_parsing = """          if (event.data.startsWith('{')) {
            const parsed = JSON.parse(event.data);
            if (Array.isArray(parsed.messages) && parsed.messages.length > 0) {
              newMsgs = parsed.messages;
            } else if (Array.isArray(parsed.data) && parsed.data.length > 0) {
              // Map Evolution API messages.update to standard format
              newMsgs = parsed.data.map((d: any) => {
                if (d.update && d.key) {
                   return { ...d, status: d.update.status || d.status, id: d.key.id, message_id: d.key.id, _is_evolution_ack: true };
                }
                return d;
              });
            } else if (parsed.message && typeof parsed.message === 'object') {
              newMsgs = [parsed.message];
            } else if (parsed.event === 'messages.update' || parsed.update) {
              newMsgs = [parsed];
            } else if (parsed.id || parsed.message_id || parsed.key) {
              newMsgs = [parsed];
            }"""

content = content.replace(old_parsing, new_parsing)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
