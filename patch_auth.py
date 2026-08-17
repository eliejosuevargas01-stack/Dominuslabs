import re

with open("project-hub/backend/app/api/endpoints/auth.py", "r") as f:
    content = f.read()

# Add SessionLocal to imports
if "from app.core.database import" in content:
    content = re.sub(r"from app.core.database import (.*)", r"from app.core.database import SessionLocal, \1", content)

old_func = """async def _maybe_provision(user: User, db: Session) -> None:
    \"\"\"
    Só chama o provisionamento se o usuário ainda não tiver
    credenciais na tabela whatsapp_accounts.
    \"\"\"
    try:
        existing = db.query(WhatsappAccount).filter(
            WhatsappAccount.user_id == user.id
        ).first()

        if existing:
            logger.debug(f"[WA-PROVISION] {user.email} já tem credenciais — pulando provisão.")
            return

        await _provision_whatsapp_client(user, db)
    except Exception as e:
        logger.error(f"[WA-PROVISION] Erro inesperado ao tentar provisionar no background para {user.email}: {e}")"""

new_func = """async def _maybe_provision(user_id: int, email: str) -> None:
    \"\"\"
    Só chama o provisionamento se o usuário ainda não tiver
    credenciais na tabela whatsapp_accounts.
    Gera uma nova sessão de banco para não compartilhar o escopo HTTP fechado.
    \"\"\"
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return

        existing = db.query(WhatsappAccount).filter(
            WhatsappAccount.user_id == user_id
        ).first()

        if existing:
            logger.debug(f"[WA-PROVISION] {email} já tem credenciais — pulando provisão.")
            return

        await _provision_whatsapp_client(user, db)
    except Exception as e:
        logger.error(f"[WA-PROVISION] Erro inesperado ao tentar provisionar no background para {email}: {e}")
    finally:
        db.close()"""

content = content.replace(old_func, new_func)
content = content.replace("background_tasks.add_task(_maybe_provision, user, db)", "background_tasks.add_task(_maybe_provision, user.id, user.email)")

with open("project-hub/backend/app/api/endpoints/auth.py", "w") as f:
    f.write(content)
