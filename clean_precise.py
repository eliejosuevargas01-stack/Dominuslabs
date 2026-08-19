import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'r') as f:
    content = f.read()

# State cleanup
content = re.sub(r'const \[credConfigured.*?\n', '', content)
content = re.sub(r'const \[credClientId, setCredClientId\].*?\n', '', content)
content = re.sub(r'const \[credClientIdInput,.*?\n', '', content)
content = re.sub(r'const \[credClientSecretInput,.*?\n', '', content)
content = re.sub(r'const \[credSecretPreview.*?\n', '', content)
content = re.sub(r'const \[showSecret.*?\n', '', content)
content = re.sub(r'const \[credSaving.*?\n', '', content)
content = re.sub(r'const \[credSuccess.*?\n', '', content)
content = re.sub(r'const \[credError.*?\n', '', content)
content = re.sub(r'const \[credCreatedAt.*?\n', '', content)
content = re.sub(r'const \[credProvisioning.*?\n', '', content)

# Remove useEffect and Handlers
content = re.sub(r'useEffect\(\(\) => \{\s*fetchCredentials\(\).*?setCredConfigured\(false\)\);\s*\}, \[\]\);', '', content, flags=re.DOTALL)
content = re.sub(r'const handleSaveCredentials = async \(\) => \{.*?\n  \};\n', '', content, flags=re.DOTALL)
content = re.sub(r'const handleProvisionCredentials = async \(\) => \{.*?\n  \};\n', '', content, flags=re.DOTALL)

# Imports cleanup
content = re.sub(r',\s*fetchCredentials,\s*saveCredentials,\s*provisionCredentials', '', content, flags=re.DOTALL)
content = content.replace("Settings, Key, Save, Eye, EyeOff", "Settings")

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'w') as f:
    f.write(content)
