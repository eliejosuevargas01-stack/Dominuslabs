import re

with open("src/pages/OmnichannelView.tsx", "r") as f:
    content = f.read()

search_block = """          for (const parsed of rawEvents) {
            if (!parsed) continue;

            if (parsed.action === 'session_disconnected') {
              setDisconnectedSessionInfo({
                session_id: parsed.session_id,
                message: parsed.message || `A sessão '${parsed.session_id}' foi desconectada.`
              });
              continue;
            }"""

replace_block = """          for (const parsed of rawEvents) {
            if (!parsed) continue;

            if (parsed.action === 'session_disconnected') {
              if (!parsed.session_id) continue;
              setDisconnectedSessionInfo({
                session_id: parsed.session_id,
                message: parsed.message || `A sessão '${parsed.session_id}' foi desconectada.`
              });
              continue;
            }"""

if search_block in content:
    content = content.replace(search_block, replace_block)

with open("src/pages/OmnichannelView.tsx", "w") as f:
    f.write(content)
