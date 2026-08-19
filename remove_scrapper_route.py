with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/App.tsx', 'r') as f:
    lines = f.readlines()

out = []
skip = False
for line in lines:
    if 'path="/scrapper"' in line:
        # We need to remove the whole Route block. Let's just remove 9 lines since <Route path="/scrapper" element={<ProtectedRoute><DashboardLayout><ScrapperView /></DashboardLayout></ProtectedRoute>} /> is 9 lines
        out.pop() # remove <Route
        skip = 8
        continue
    if skip > 0:
        skip -= 1
        continue
    out.append(line)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/App.tsx', 'w') as f:
    f.writelines(out)
