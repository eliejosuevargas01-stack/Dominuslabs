import json, os, subprocess
cmd = "python3 ~/.gemini/config/skills/jules-reviewer/scripts/jules_session.py --list"
out = subprocess.check_output(cmd, shell=True, text=True)
# The output starts with some text, then a JSON. We need to extract the JSON.
json_start = out.find("{")
data = json.loads(out[json_start:])
for s in data.get("sessions", []):
    print(f"ID: {s['id']}, State: {s.get('state')}, Prompt: {s.get('prompt')[:50]}")
