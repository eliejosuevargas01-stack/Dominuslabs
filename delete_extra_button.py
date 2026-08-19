import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'r') as f:
    content = f.read()

# Delete the button block
pattern = r'<button\s*onClick=\{handleProvisionCredentials\}.*?</button>'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'w') as f:
    f.write(content)
