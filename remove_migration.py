import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/main.py', 'r') as f:
    content = f.read()

# We need to remove the block between "# Auto-migration" and "print(f"Auto-migration failed: {e}")"
content = re.sub(r'# Auto-migration\ntry:.*?except Exception as e:\n    print\(f"Auto-migration failed: \{e\}"\)\n', '', content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/main.py', 'w') as f:
    f.write(content)
