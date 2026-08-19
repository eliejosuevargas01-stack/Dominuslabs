import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

# Update import
content = content.replace("import { fetchCompanySettings, updateCompanySettings, uploadProductMedia,", "import { fetchCompanySettings, updateCompanySettings, uploadProductMedia, getUserTenant,")
content = content.replace("fetchCompanySettings(\"default\")", "fetchCompanySettings(getUserTenant())")
content = content.replace("updateCompanySettings(settings, \"default\")", "updateCompanySettings(settings, getUserTenant())")

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)

print("Patched CompanySettingsView.tsx successfully.")
