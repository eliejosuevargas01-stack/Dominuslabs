import re

with open('project-hub/backend/.env.example', 'r') as f:
    content = f.read()

# Use regex to remove MTLS blocks and variables
content = re.sub(r'# --- mTLS CERTIFICATES.*?(?=# Worker Configs)', '', content, flags=re.DOTALL)
content = re.sub(r'ENABLE_MTLS="true"\n', '', content)
content = re.sub(r'# mTLS Certificate Paths.*?\nMTLS_CERT_PATH=".*?"\nMTLS_KEY_PATH=".*?"\nMTLS_CA_CERT_PATH=".*?"\n', '', content, flags=re.DOTALL)

with open('project-hub/backend/.env.example', 'w') as f:
    f.write(content.strip() + '\n')
