import json
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/.env')

data = json.loads("""
{
  "_encrypted": true,
  "encryptedKey": "jqFd520l5t4W+ABFT8mwUubJ+KL/YUB1tU38ka5EpFnlQTBI/pxYz8aWK49Ck/Bi9UA2oNtLOXrE1ZIhoycKJNNqMbFu5M5CyVu1eia/uUi3KzkbAjgnrzAVQj/vabApTdjqlvXoUEULY3wUDl5xZnabBiOscaDnOEH+QJL5+ftEiGg+ztAKwvyEl+V2f8TkusEgVxKOLG3U4dgTJJuBadz3LP6YXzKdKA2rko4iKLatbgH5v0R45UonPfhPkVec3Zd7AI1s24zYycj91tETFTxzM01MEVHJZnjiAlgA9Z8k91yWYyecPeTbzy6vyuS4M3V4ZJfFxCHwzfIZg0o2zg==",
  "iv": "iwDhDP2dMOZ3g2x5S4RjYQ==",
  "authTag": "raQIhttqSy9iNrNID+CWjg==",
  "payload": "M44WYaxNe/k8T8SArTuGcVnL+tb4Jj2r3gsD3RZ+aCToKtpWPg3mFMjMi/VR0RhjWZ/siJhk8+qaz8+G7TViHCslO+JvFPhQWaO08usUtRDLe/ivNGBUGucDOcQlzJ54BReDQkiJVUIXtJX4hYIoYLiGZlzH6lBA0vxaqaCnGS8v1VATTKpnuHesP0yY8in7u5EiWwUy1znrZsEznral3N8foLi6PiycHs3JMTSv0tG6FaVrrC+HBRwUNgfNE9YO1hgc9rL3UfveA5EK1cB3ii5UkWRs9P5BgpyqtJPcoKlREAYAUrFqDpBM8jMQprFFyGCiy0YZV203zjLvVydCoTEXKsr+q8o1SxIqPmsKoCUO4y8P+do0vzHw2EkUQtHyL/9Ym1pCg5qWhINghfwL/Pn038wyvY7POhvMfHxUDkBAfMBfZ6TXTd7mld9bknxAHC/exXiNWHcMbWhGQRZsChMcpN4MEZaNL/N/VyJhcwEP4+EfV+LtR8+SLpYCHblRnqCfkQFENkRDRRO2ER4X+YxWbQUrZUuNWgzJHZa2A4qBqLCJC+iOuKp32OfDURCMe7Of49lCBso+Bk3UV8i5VC/yb/Y171VUaDiiBiRtGLXWVQvPPYPIRQZHijMV1yX+CQ1F4Ze0XuGdmd1ycf0ImLLS4j0eMltIO7s+B8O9uJxUAW17rGaLcoZlp6fEMsYA9G8yBe1x6niPrOP1H7Sd2X/dPMDpcBgylq71UeS/GIHiErQe"
}
""")

env_vars = {}
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/.env', 'r') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'): continue
        if '=' in line:
            k, v = line.split('=', 1)
            if v.startswith('"') and v.endswith('"'): v = v[1:-1]
            env_vars[k] = v

keys_to_test = []
for k, v in env_vars.items():
    if "BEGIN PRIVATE KEY" in v:
        keys_to_test.append((k, v.replace("\\n", "\n")))

for k, v in keys_to_test:
    try:
        private_key = serialization.load_pem_private_key(v.encode('utf-8'), password=None)
    except Exception as e:
        print(f"Failed to load key {k}: {e}")
        continue
    
    encrypted_key = base64.b64decode(data["encryptedKey"])
    pads = [
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None),
        padding.PKCS1v15()
    ]
    
    for pad in pads:
        try:
            aes_key = private_key.decrypt(encrypted_key, pad)
            iv = base64.b64decode(data["iv"])
            auth_tag = base64.b64decode(data["authTag"])
            ciphertext = base64.b64decode(data["payload"])
            
            decryptor = Cipher(algorithms.AES(aes_key), modes.GCM(iv, auth_tag)).decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            print(f"SUCCESS with key {k} and pad {pad}!")
            print(plaintext.decode('utf-8'))
            exit(0)
        except Exception as e:
            pass
            
print("No keys worked.")
