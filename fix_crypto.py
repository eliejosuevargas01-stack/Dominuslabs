import re

file_path = "project-hub/backend/app/core/crypto.py"
with open(file_path, "r") as f:
    content = f.read()

old_block = """        payload_bytes = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
        try:
            return json.loads(payload_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            # Se não for JSON, retorna a string pura
            return payload_bytes.decode('utf-8')"""

new_block = """        payload_bytes = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
        try:
            decrypted_json = json.loads(payload_bytes.decode('utf-8'))
            if isinstance(decrypted_json, dict):
                # Preserve top-level metadata keys from the encrypted payload (like session_id, tenant_id)
                for k, v in encrypted_data.items():
                    if k not in {"_encrypted", "encryptedKey", "iv", "authTag", "payload"}:
                        if k not in decrypted_json:
                            decrypted_json[k] = v
            return decrypted_json
        except json.JSONDecodeError:
            # Se não for JSON, retorna a string pura
            return payload_bytes.decode('utf-8')"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, "w") as f:
        f.write(content)
    print("crypto.py fixed.")
else:
    print("Could not find old block in crypto.py")
