import json
from base64 import b64decode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
import os

load_dotenv()

encrypted_data = {
    "_encrypted": True,
    "encryptedKey": "oUEuAJj7dyEHJYAnNzOxO6fkeKQ5aGbhWtZz7C3iUwGqv/n3EilsqcFOZQHgLtTh/pyByT+cVBZrrVMqaKQj3MyZLeE91pKqycL+paZVqnN/WhPuHFDbFNa1vJ5PkF2lj3LP61/mwP37tX6h56pI1uPRzcws9cwthrt21gPZ25pD0rV1an6v0Awk29aJL/LAhuAfGVQ3qVYUggrZQfX+ZXcVku+kmVSI6EjQmVJfWnGYD+VhO4MaToiKxfpk2Xx40c3UEauI3A71EQERqbmJpvAXnJtjDkRavD4XZpHotHdzprIb1sqYRifBKcZdJ0looyz2GsQ1YV4FH4uB5nil3A==",
    "iv": "3DC1GqBgRoJ0dkX76Do4Nw==",
    "authTag": "dYJs5ON+O7E9rz1ST3xfqA==",
    "payload": "/hB/dSbBXvrgofE6p5lKavQOvNKcLxqPGX/xV/qJUUXH6v1XLPLcCHAiCG851T9RX1d2TpmR6ksGrJeHcVa/m4nKOFs/9JSefDMpwwau9mVm54R2xR6QyBqIIam834keCKhlJhtLzypBfvsYeVK8TFA3nhcBhItnXpbekiEupW9m6B9+bXnPYUzmnFqrZNANd5UonPfrkkwYrcgD7lCpn4oCECvQ8YqcsYqTBNGglALcqLVALclJYvYaNHjOomHvUq3wDMgoPLb1cDvBxYh57f+rrn07tK6jv5b7m+/d4wd2qvNsmlNd31z3NYwncaZ3i3soOyNM8SbFdjrKiRDVHENIoPRlp86Tfa8ruQzlWxkLYVNErKD6ePhZvV0zV69ISh7e/B4HfOGoX7HL71+s4HPX791Hr8TazG6DbkdfnUJVCqX5MjdTYNd+dx5KUKZTjG/q8cSSBNypbxZAgF/HVhoHSmshM2fWWEPsnJ+lROovxj+PAP5YNR++uVcMAIkpI8baOD2C8nbCbzQ4HjiQ9dNhYnp2Vmk64xD+GyJT5QouOyQqgJAPn843lz5HJ6w4PMTBLKJzjWc6wPyJvscbT9PLIHbwQBwywkDXdpYR1RDoYDe56ZKWu+zJ7u8LgYbeA/ftsKr1k4CDBcuGB3Cz7U48u6Xm+WQ1cbKCCMzREzpFcUmvfBhakOg+7BCwJ+ISnqIPcbTetrLQ+t87JZUlLsdmAIN2HbAdKgGC85DZW6e00bSSJxnYvyRU5jjRBcbsbx3MaqCcnWWc42YGaVdjH2TnH6hHsE2lWUgKd7T61QcULwXeQSxtqQ=="
}

def clean_pem(pem_str: str) -> str:
    lines = [line.strip() for line in pem_str.strip().split('\n') if line.strip()]
    if lines[0].startswith("-----BEGIN"):
        pass
    else:
        lines.insert(0, "-----BEGIN PRIVATE KEY-----")
        lines.append("-----END PRIVATE KEY-----")
    return "\n".join(lines)

private_key_pem = clean_pem(os.getenv("DOMINUS_PRIVATE_KEY"))
private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)

encrypted_key_b64 = encrypted_data["encryptedKey"]
iv_b64 = encrypted_data["iv"]
auth_tag_b64 = encrypted_data["authTag"]
payload_b64 = encrypted_data["payload"]

encrypted_key = b64decode(encrypted_key_b64)
iv = b64decode(iv_b64)
auth_tag = b64decode(auth_tag_b64)
ciphertext = b64decode(payload_b64)

aes_key = private_key.decrypt(
    encrypted_key,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

aesgcm = AESGCM(aes_key)
payload_bytes = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
decrypted = json.loads(payload_bytes.decode('utf-8'))
print("DECRYPTED:", decrypted)
print("TYPE:", type(decrypted))
