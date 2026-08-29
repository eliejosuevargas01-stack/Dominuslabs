import sys, time, json, urllib.request, os

api_key = os.environ.get("JULES_API_KEY")
if not api_key:
    # try getting it from .env.example
    env_path = os.path.expanduser("~/.gemini/config/skills/jules-reviewer/.env.example")
    with open(env_path) as f:
        for line in f:
            if line.startswith("JULES_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip("\"'")
                break

req = urllib.request.Request("https://jules.googleapis.com/v1alpha/sessions/14332837140454058259", headers={"X-Goog-Api-Key": api_key})

print("Vigiando...")
while True:
    try:
        resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        state = resp.get("state")
        print(f"[{time.strftime('%H:%M:%S')}] Polling...")
        if state == "COMPLETED" or state == "ERROR":
            print("🚨 EVENTO JULES DETECTADO: " + state)
            sys.exit(0)
    except Exception as e:
        print("Erro de rede:", e)
    time.sleep(30)
