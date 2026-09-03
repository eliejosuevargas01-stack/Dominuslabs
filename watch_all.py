import sys, time, json, urllib.request, os

api_key = os.environ.get("JULES_API_KEY")
if not api_key:
    env_path = os.path.expanduser("~/.gemini/config/skills/jules-reviewer/.env.example")
    with open(env_path) as f:
        for line in f:
            if line.startswith("JULES_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip("\"'")
                break

sessions = {
    "6769183704892538388": "A-Security",
    "3427494502986466512": "B-Tests-CRM",
    "12022919900430597365": "C-Tests-WA"
}
completed = set()

print("Vigiando 3 sessoes (A-Security, B-Tests-CRM, C-Tests-WA)...")
while len(completed) < 3:
    for sid, label in sessions.items():
        if sid in completed:
            continue
        req = urllib.request.Request(
            f"https://jules.googleapis.com/v1alpha/sessions/{sid}",
            headers={"X-Goog-Api-Key": api_key}
        )
        try:
            resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
            state = resp.get("state")
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] {label} ({sid}) -> {state}")
            if state in ("COMPLETED", "ERROR"):
                completed.add(sid)
            elif state == "AWAITING_USER_FEEDBACK":
                print(f"  *** {label} PRECISA DE RESPOSTA! ***")
        except Exception as e:
            print(f"Erro {label}:", e)
    if len(completed) < 3:
        time.sleep(30)

print("TODAS AS 3 SESSOES FINALIZARAM!")
sys.exit(0)
