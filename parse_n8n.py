import json
import os

files = [
    "/home/eliezer/Descargas/Dominus AI.json",
    "/home/eliezer/Descargas/dominuslabs_crm.json",
    "/home/eliezer/Descargas/dominuslabs_respostas_leads.json"
]

for filepath in files:
    filename = os.path.basename(filepath)
    print(f"\n{'='*50}\nAnalyzing {filename}...\n{'='*50}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        nodes = data.get('nodes', [])
        print(f"Total Nodes: {len(nodes)}")
        
        for node in nodes:
            node_type = node.get('type', '')
            node_name = node.get('name', '')
            parameters = node.get('parameters', {})
            
            # Identify HTTP requests (webhooks/API calls)
            if 'httpRequest' in node_type.lower() or 'webhook' in node_type.lower():
                url = parameters.get('url', 'N/A')
                method = parameters.get('method', 'GET')
                print(f"[{node_type}] {node_name}")
                if 'dominuslabs' in str(url).lower() or 'api' in str(url).lower() or 'webhook' in str(url).lower() or url != 'N/A':
                    print(f"  Method: {method}")
                    print(f"  URL: {url}")
                    
                    # check for body
                    if parameters.get('sendBody'):
                        body = parameters.get('bodyParameters', parameters.get('jsonBody', 'No body found'))
                        print(f"  Body: {body}")
                print("-" * 30)
                
    except Exception as e:
        print(f"Error reading {filename}: {e}")
