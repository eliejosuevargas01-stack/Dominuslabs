import csv
import json
import re

# Read CSV
with open('network_capture_20260922_102725.csv', 'r', encoding='utf-8', errors='replace') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Collect all cardapio data
all_data = []
for r in rows:
    if 'estabelecimento-cardapio' not in r.get('url', ''):
        continue
    body = r.get('response_body', '')
    if body and 'Error reading' not in body and body != '{"data":null}':
        all_data.append(body)

# Parse products
produtos = {}
for body in all_data:
    # Extract product blocks
    product_blocks = re.findall(r'\{"id":"(\d+)".*?"cardapio_elementos":\[.*?\]\}', body, re.DOTALL)
    
    for block in product_blocks:
        try:
            # Get product data
            pid = re.search(r'"id":"(\d+)"', block)
            nome = re.search(r'"des_item":"([^"]+)"', block)
            cat = re.search(r'"des_categoria":"([^"]+)"', block)
            status = re.search(r'"ind_status":"([^"]+)"', block)
            preco_match = re.search(r'"val_preco":"([^"]+)"', block)
            
            if pid:
                produtos[pid.group(1)] = {
                    'id': pid.group(1),
                    'nome': nome.group(1) if nome else 'N/A',
                    'categoria': cat.group(1) if cat else 'N/A',
                    'status': status.group(1) if status else 'N/A',
                    'preco': preco_match.group(1) if preco_match else 'N/A'
                }
        except:
            pass

# Save to file
output = []
for p in produtos.values():
    output.append(p)

with open('produtos.csv', 'w', encoding='utf-8') as f:
    f.write('id,nome,categoria,status,preco\n')
    for p in output:
        nome = p['nome'].replace('"', '""')
        f.write(f'{p["id"]},"{nome}",{p["categoria"]},{p["status"]},{p["preco"]}\n')

print(f'✅ {len(output)} produtos salvos em produtos.csv')
for i, p in enumerate(output[:10], 1):
    print(f'{i}. {p["nome"][:50]}... - R$ {p["preco"]}')
