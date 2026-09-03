import json
import os

files = [
    "/home/eliezer/Descargas/Dominus AI.json",
    "/home/eliezer/Descargas/dominuslabs_crm.json",
    "/home/eliezer/Descargas/dominuslabs_respostas_leads.json"
]

for filepath in files:
    filename = os.path.basename(filepath)
    print(f"\n{'='*50}\nAnalyzing HTTP Requests in {filename}...\n{'='*50}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        nodes = data.get('nodes', [])
        
        for node in nodes:
            node_type = node.get('type', '')
            node_name = node.get('name', '')
            parameters = node.get('parameters', {})
            
            if 'httpRequest' in node_type:
                url = parameters.get('url', 'N/A')
                method = parameters.get('method', 'GET')
                print(f"[HTTP] {node_name}")
                print(f"  Method: {method}")
                print(f"  URL: {url}")
                
                send_body = parameters.get('sendBody', False)
                send_headers = parameters.get('sendHeaders', False)
                
                if parameters.get('specifyBody') == 'json' and 'jsonBody' in parameters:
                    print(f"  JSON Body: {parameters.get('jsonBody')}")
                elif send_body and 'bodyParameters' in parameters:
                    print(f"  Body Params: {parameters.get('bodyParameters')}")
                
                if send_headers and 'headerParameters' in parameters:
                    print(f"  Headers: {parameters.get('headerParameters')}")
                    
                print("-" * 30)
                
    except Exception as e:
        print(f"Error reading {filename}: {e}")
