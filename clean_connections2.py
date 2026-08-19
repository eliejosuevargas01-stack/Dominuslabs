with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'r') as f:
    lines = f.readlines()

out = []
skip = 0
for i, line in enumerate(lines):
    if "fetchCredentials()" in line:
        skip = 10
        continue
    if "const handleProvisionCredentials" in line:
        skip = 19
        continue
    if skip > 0:
        skip -= 1
        continue
    out.append(line)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'w') as f:
    f.writelines(out)
