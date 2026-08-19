import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/services/api.ts', 'r') as f:
    content = f.read()

new_func = """
export function getUserTenant(): string {
  const token = localStorage.getItem("admin_token");
  if (!token) return "default";
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return "default";
    const payload = JSON.parse(atob(parts[1]));
    return payload.tenant_id || "default";
  } catch (e) {
    return "default";
  }
}
"""

if "getUserTenant" not in content:
    content = content.replace("export function getUserRole(): string {", new_func + "\nexport function getUserRole(): string {")
    with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/services/api.ts', 'w') as f:
        f.write(content)
    print("Patched api.ts successfully.")
else:
    print("Already patched.")
