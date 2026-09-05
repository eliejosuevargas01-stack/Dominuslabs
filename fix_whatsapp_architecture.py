import re
import os

file_path = "project-hub/backend/app/api/endpoints/whatsapp.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix 1: Event loop blocking in get_user_m2m_headers
# We need to import run_in_threadpool
if "from fastapi.concurrency import run_in_threadpool" not in content:
    content = content.replace("from fastapi import", "from fastapi.concurrency import run_in_threadpool\nfrom fastapi import")

old_query = "user = db.query(User).filter(User.email == email).first()"
new_query = "user = await run_in_threadpool(lambda: db.query(User).filter(User.email == email).first())"
content = content.replace(old_query, new_query)

# Fix 2: save_credentials Data Loss
old_save = """    if hasattr(account, "tenant_id") and getattr(user, "tenant_id", None):
        account.tenant_id = user.tenant_id
    if hasattr(account, "idpw"):
        account.idpw = payload.client_id
    if hasattr(account, "client_id"):
        account.client_id = payload.client_id

    db.commit()"""
new_save = """    if hasattr(account, "tenant_id") and getattr(user, "tenant_id", None):
        account.tenant_id = user.tenant_id
    if hasattr(account, "idpw"):
        account.idpw = payload.client_id
    if hasattr(account, "client_id"):
        account.client_id = payload.client_id
    
    account.client_secret = payload.client_secret

    db.commit()"""
content = content.replace(old_save, new_save)

# Fix 3: socket.gethostbyname
old_dns = "socket.gethostbyname(parsed.hostname)"
new_dns = "await asyncio.get_running_loop().getaddrinfo(parsed.hostname, None)"
if "import asyncio" not in content:
    content = "import asyncio\n" + content
content = content.replace(old_dns, new_dns)

# Fix 4: SSL Check
old_ssl = """        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE"""
new_ssl = """        # ctx.check_hostname = False
        # ctx.verify_mode = ssl.CERT_NONE"""
content = content.replace(old_ssl, new_ssl)

with open(file_path, "w") as f:
    f.write(content)
print("Architecture fixed!")
