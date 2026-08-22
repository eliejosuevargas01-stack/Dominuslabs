with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_b = """                    return (
                      <div
                        key={msg.message_id || index}
                        id={`msg-${msg.message_id || index}`}"""

new_b = """                    if (!rawContent && !msg.image_url && !msg.video_url && !msg.audio_url && !msg.document_url && !msg.system_message) {
                      return null;
                    }
                    return (
                      <div
                        key={msg.message_id || index}
                        id={`msg-${msg.message_id || index}`}"""

content = content.replace(old_b, new_b)
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
