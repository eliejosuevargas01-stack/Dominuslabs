import re

file_path = "src/App.tsx"
with open(file_path, "r") as f:
    content = f.read()

import_statement = "import OrderManagerView from './pages/OrderManagerView';\n"
if "import OrderManagerView" not in content:
    content = content.replace("import Login from './pages/Login';", "import Login from './pages/Login';\n" + import_statement)

route_statement = """          <Route 
            path="/order-manager" 
            element={
              <ProtectedRoute>
                <OrderManagerView />
              </ProtectedRoute>
            } 
          />
"""

if "/order-manager" not in content:
    content = content.replace("          {/* Default fallback redirects */}", route_statement + "          {/* Default fallback redirects */}")

with open(file_path, "w") as f:
    f.write(content)
print("App.tsx fixed.")
