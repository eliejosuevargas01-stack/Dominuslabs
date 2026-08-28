import time
import requests

time.sleep(15)

payload = {
  "tenant_id": "admin",
  "pedido_id": "8b9a2c-test-order",
  "content_jid": "conversation",
  "localização": "Av. Teste Local, 999",
  "items": [
    {
      "codigo": "burger-01",
      "nome": "Hambúrguer de Teste Local",
      "quantidade": 1,
      "subtotal": "29.90"
    }
  ],
  "cliente_id": "554799999999@s.whatsapp.net"
}

headers = {
    "X-Master-API-Key": "dominuslabs-master-s2s-key-2026", # Local master key
    "Content-Type": "application/json"
}

res = requests.post("http://localhost:8001/api/v1/orders", json=payload, headers=headers)
print(res.status_code, res.text)
