import json
import urllib.request
import time
import sys

status_url = "https://myn8n.seommerce.shop/webhook/deepresearch_status?id=9999999"
headers = {
    "Content-Type": "application/json",
    "x-apify-secret": "bowT7Vwgclr4bUcJd80xZXgyVmI2HzjQdCRYNKX8rjiq3TorPWyw3EiHezLK7hygLlsah6ZLvZmuZf2XIjFmwk6UrtWT26a8OnKGwwje9aDEGLiHMU9N6FYhcO04326B"
}

print("Aguardando o N8N processar (polling a cada 30s)...")
for i in range(20):
    time.sleep(30)
    try:
        status_req = urllib.request.Request(status_url, headers=headers, method="GET")
        with urllib.request.urlopen(status_req) as response:
            status_data = json.loads(response.read().decode("utf-8"))
            if isinstance(status_data, list) and len(status_data) > 0:
                status_data = status_data[0]
            
            status = status_data.get("status", "").lower()
            print(f"Tentativa {i+1}: Status = {status}")
            if status == "entregue":
                print("\nRELATÓRIO FINAL OBTIDO!")
                with open("/home/eliezer/.gemini/antigravity/brain/612c379d-826d-4fa5-9e38-d1c821de5f56/research_report.json", "w") as f:
                    json.dump(status_data, f, indent=2, ensure_ascii=False)
                sys.exit(0)
    except Exception as e:
        print(f"Tentativa {i+1}: Erro no polling:", str(e))
