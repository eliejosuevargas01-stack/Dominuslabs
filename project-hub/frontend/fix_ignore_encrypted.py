with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_block = """                  sortedMessages.map((msg, index) => {
                    const isMe = msg.is_from_me === true || msg.sender === 'user';"""

new_block = """                  sortedMessages.map((msg, index) => {
                    if (msg._encrypted === true) return null; // Ignore encrypted raw webhooks

                    const isMe = msg.is_from_me === true || msg.sender === 'user';"""

content = content.replace(old_block, new_block)

# Also ensure empty bubbles don't render if there's no media and no text at all
old_bubble = """                    return (
                      <div
                        key={msg.id || msg.message_id || index}
                        id={`msg-${msg.id || msg.message_id || index}`}"""

new_bubble = """                    if (!rawContent && !msg.image_url && !msg.video_url && !msg.audio_url && !msg.document_url && !isReaction && !msg.system_message) {
                      return null; // Do not render completely empty bubbles (usually ACKs or unhandled types)
                    }
                    
                    return (
                      <div
                        key={msg.id || msg.message_id || index}
                        id={`msg-${msg.id || msg.message_id || index}`}"""
                        
content = content.replace(old_bubble, new_bubble)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
