import re

with open("app/api/endpoints/webhooks.py", "r") as f:
    content = f.read()

# We can replace the duplicated logic.
# Wait, let's write a python script to refactor this nicely.
