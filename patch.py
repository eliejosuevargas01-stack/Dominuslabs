import os
import json
import urllib.request
import urllib.error
import time

def run_deep_research(query: str) -> str:
    """
    Dispara o fluxo de Pesquisa Profunda no n8n.
    O webhook deve ser configurado via variável de ambiente N8N_RESEARCH_WEBHOOK.
    A tool faz o disparo e depois faz polling no endpoint de status até que esteja "entregue".
    """
    webhook_url = os.environ.get("N8N_RESEARCH_WEBHOOK", "https://myn8n.seommerce.shop/webhook/deep-research")
    status_url = "https://myn8n.seommerce.shop/webhook/deepresearch_status"
    
    payload = {
        "tema": query,
        "webhook_callback": "https://myn8n.seommerce.shop/webhook/deep-research-callback"
    }
    headers = {"Content-Type": "application/json"}
    
    req = urllib.request.Request(webhook_url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            init_resp = response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Erro HTTP {e.code} ao iniciar pesquisa no n8n: {e.read().decode('utf-8')}"
    except Exception as e:
        return f"Erro de conexão com n8n ao iniciar pesquisa: {str(e)}"
        
    # Polling for completion
    max_attempts = 30 # 30 * 10 seconds = 5 minutes
    for attempt in range(max_attempts):
        time.sleep(10)
        try:
            status_req = urllib.request.Request(status_url, headers=headers, method='GET')
            with urllib.request.urlopen(status_req) as response:
                status_data = json.loads(response.read().decode('utf-8'))
                
                # Assuming the response is a JSON object with 'status' and 'relatorio' or similar
                if isinstance(status_data, list) and len(status_data) > 0:
                    status_data = status_data[0]
                    
                status = status_data.get("status", "").lower()
                if status == "entregue":
                    return status_data.get("relatorio", json.dumps(status_data, indent=2, ensure_ascii=False))
                
        except Exception as e:
            # Ignore polling errors and retry
            pass

    return "A pesquisa profunda excedeu o tempo limite de espera (5 minutos). Verifique o n8n manualmente."
