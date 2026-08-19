import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'r') as f:
    content = f.read()

# Remove unused imports
content = content.replace("Settings, Key, Save, Eye, EyeOff", "Settings")

# Remove unused states
content = re.sub(r'const \[credConfigured.*?\n', '', content)
content = re.sub(r'const \[credClientId, setCredClientId\].*?\n', '', content)
content = re.sub(r'const \[credSecretPreview.*?\n', '', content)
content = re.sub(r'const \[showSecret.*?\n', '', content)
content = re.sub(r'const \[credSaving.*?\n', '', content)
content = re.sub(r'const \[credSuccess.*?\n', '', content)
content = re.sub(r'const \[credError.*?\n', '', content)
content = re.sub(r'const \[credCreatedAt.*?\n', '', content)

# Remove unused handleSaveCredentials function
content = re.sub(r'const handleSaveCredentials = async \(\) => \{.*?\n  \};\n', '', content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'w') as f:
    f.write(content)
