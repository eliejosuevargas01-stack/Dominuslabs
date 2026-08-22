with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_cond = "if (!rawContent && !msg.image_url && !msg.video_url && !msg.audio_url && !msg.document_url && !msg.system_message) {"
new_cond = "if (!rawContent && !msg.image_url && !msg.video_url && !msg.audio_url && !msg.document_url && !msg.system_message && !msg.media_url && !msg.url && !msg.file_url) {"
content = content.replace(old_cond, new_cond)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
