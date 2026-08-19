with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'r') as f:
    lines = f.readlines()

# delete 481 to 593 inclusive (index 480 to 592)
del lines[480:593]

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/ConnectionsView.tsx', 'w') as f:
    f.writelines(lines)
