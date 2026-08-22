with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# Add a check before rendering a bubble
old_map = """{chatMessages.map((msg, idx) => {"""
new_map = """{chatMessages.map((msg, idx) => {
                  const extracted = extractContent(msg);
                  if (!extracted && !msg.image_url && !msg.video_url && !msg.document_url && !msg.audio_url) return null;
"""

content = content.replace(old_map, new_map)

# Also need to make sure extractContent is available inside the render scope, or we just redefine it locally if it's not.
# wait, extractContent is defined inside the SSE handler! It's not available in the render scope.
