with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/main.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("    try:") and "SessionLocal" in lines[lines.index(line)+1]:
        # It should be inside startup() or just at root level?
        pass

# Let's just fix it by replacing the whole block properly
