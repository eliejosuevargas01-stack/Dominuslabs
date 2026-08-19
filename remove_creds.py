import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'r') as f:
    content = f.read()

# Remove the block in JSX
content = re.sub(r'\{/\* ================================================================ \*/\}\s*\{/\* Credenciais da WhatsApp API\s*\*/\}\s*\{/\* ================================================================ \*/\}.*?</button>\s*</div>\s*</div>\s*</div>\s*</div>', '</div>', content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'w') as f:
    f.write(content)
