from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from sqlalchemy.orm import Session
import os

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.middleware import AuditLoggingMiddleware, DecryptionMiddleware

# Import all models to ensure they are registered on Base.metadata
from app.models.project import Project
from app.models.asset import ProjectAsset
from app.models.task import ProjectTask
from app.models.logs import CommitLog, DeployLog
from app.models.feedback import Feedback
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount

# Create persistent upload folders and database tables
os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "audio"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "documents"), exist_ok=True)

Base.metadata.create_all(bind=engine)

# Auto-migration for SQLite
try:
    from app.core.database import SessionLocal
    import sqlite3
    db = SessionLocal()
    conn = db.get_bind().raw_connection()
    c = conn.cursor()
    
    # 1. Add delivery fields
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_fee_type VARCHAR DEFAULT "Fixo";')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_fee_value FLOAT DEFAULT 0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_radius_km FLOAT DEFAULT 0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_max_coverage_km FLOAT DEFAULT 20.0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN minimum_order_value FLOAT DEFAULT 0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN preparation_time_minutes INTEGER DEFAULT 0;')
    except Exception: pass
        
    # 2. Add promotions field
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN promotions JSON DEFAULT "[]";')
    except Exception: pass

    # 3. Add product_media table
    try:
        c.execute('''
        CREATE TABLE IF NOT EXISTS product_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id VARCHAR NOT NULL DEFAULT 'default',
            product_id VARCHAR NOT NULL,
            media_type VARCHAR NOT NULL,
            media_url VARCHAR NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS ix_product_media_tenant_id ON product_media(tenant_id);')
        c.execute('CREATE INDEX IF NOT EXISTS ix_product_media_product_id ON product_media(product_id);')
    except Exception: pass

    conn.commit()
    db.close()
except Exception as e:
    print(f"Auto-migration failed: {e}")


# Automatic database migration for users and whatsapp_accounts columns
from sqlalchemy import text
db_type = engine.url.drivername
if "sqlite" in db_type:
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("users")]
        with engine.begin() as conn:
            if "tenant_id" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tenant_id VARCHAR(255);"))
            if "whatsapp_token" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN whatsapp_token VARCHAR;"))
            if "access_token" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN access_token VARCHAR;"))
            if "refresh_token" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN refresh_token VARCHAR;"))
            if "token_issued_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN token_issued_at DATETIME;"))
            if "token_expires_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN token_expires_at DATETIME;"))
            
            if "preferred_session_id" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN preferred_session_id VARCHAR(255);"))
            if "permissions" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN permissions VARCHAR(255) DEFAULT 'read';"))
            
            wa_columns = [c["name"] for c in inspector.get_columns("whatsapp_accounts")] if inspector.has_table("whatsapp_accounts") else []
            if "tenant_id" not in wa_columns and inspector.has_table("whatsapp_accounts"):
                conn.execute(text("ALTER TABLE whatsapp_accounts ADD COLUMN tenant_id VARCHAR(255);"))
        print("SQLite migration: users and whatsapp_accounts tenant_id/permissions columns checked/added successfully.")
    except Exception as e:
        print(f"SQLite migration warning: {e}")
else:
    # Postgres DDL executions in separate transactions
    ddl_statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_token VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_session_id VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions VARCHAR(255) DEFAULT 'read';",
        "ALTER TABLE users ALTER COLUMN can_create_projects DROP NOT NULL;",
        "ALTER TABLE users ALTER COLUMN can_edit_projects DROP NOT NULL;",
        "ALTER TABLE users ALTER COLUMN can_manage_crm DROP NOT NULL;",
        "ALTER TABLE users ALTER COLUMN can_use_scrapper DROP NOT NULL;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS access_token TEXT;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS refresh_token TEXT;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_issued_at TIMESTAMP;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMP;",
        "ALTER TABLE whatsapp_accounts ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255);"
    ]
    for stmt in ddl_statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception as stmt_err:
            print(f"Postgres migration DDL notice ({stmt}): {stmt_err}")
    print("PostgreSQL migration: users and whatsapp_accounts columns migration completed.")

# Seed database users
def seed_database_users():
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash
    import secrets
    db = SessionLocal()
    try:
        # Seed main admin
        admin_email = settings.ADMIN_USERNAME
        if "@" not in admin_email:
            admin_email = f"{settings.ADMIN_USERNAME}@dominuslabs.online"
            
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin",
                permissions="read,write,update,delete",
                whatsapp_token=f"wa_tok_{secrets.token_hex(16)}"
            )
            db.add(admin_user)
        else:
            if not existing_admin.whatsapp_token:
                existing_admin.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"
            
        # Seed default viewer / patrik user
        viewer_email = settings.VIEWER_USERNAME
        if "@" not in viewer_email:
            viewer_email = "patrik182rodrigues@gmail.com"
            
        existing_viewer = db.query(User).filter(User.email == viewer_email).first()
        if not existing_viewer:
            viewer_user = User(
                email=viewer_email,
                hashed_password=get_password_hash(settings.VIEWER_PASSWORD),
                role="custom",
                permissions="read,write",
                whatsapp_token=f"wa_tok_{secrets.token_hex(16)}"
            )
            db.add(viewer_user)
        else:
            if not existing_viewer.whatsapp_token:
                existing_viewer.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"
            
        db.commit()
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

seed_database_users()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enterprise Audit Logging Middleware
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(DecryptionMiddleware)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    allow_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
    # In CORS spec, allow_credentials must be False if using wildcard '*'
    allow_credentials = False if "*" in allow_origins else True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

from fastapi.responses import RedirectResponse, Response
from typing import Optional

@app.get("/api/sessions/{session_id}/avatar")
@app.get("/avatar")
async def root_avatar_proxy(
    session_id: Optional[str] = None,
    session: Optional[str] = None,
    jid: Optional[str] = None
):
    """
    Proxy de avatar direto consumido pelo frontend sem necessidade de pré-processamento.
    Mapeia rotas relativas exatas devolvidas pelo n8n:
    - /api/sessions/{session_id}/avatar?jid=...
    - /avatar?session={session_id}&jid=...
    """
    target_session = session_id or session
    if not jid:
        raise HTTPException(status_code=400, detail="Parâmetro 'jid' é obrigatório.")

    try:
        from app.api.endpoints.whatsapp import make_whatsapp_api_request
        paths_to_try = []
        if target_session and target_session != "default":
            paths_to_try.append(f"/api/sessions/{target_session}/avatar?jid={jid}&json=true")
            paths_to_try.append(f"/avatar?session={target_session}&jid={jid}&json=true")
            paths_to_try.append(f"/api/sessions/{target_session}/avatar?jid={jid}")
            paths_to_try.append(f"/avatar?session={target_session}&jid={jid}")
        paths_to_try.append(f"/avatar?jid={jid}&json=true")
        paths_to_try.append(f"/avatar?jid={jid}")

        for clean_path in paths_to_try:
            try:
                res = await make_whatsapp_api_request("GET", clean_path)
                if isinstance(res, dict):
                    if res.get("_is_binary") and res.get("content"):
                        return Response(
                            content=res["content"],
                            media_type=res.get("content_type") or "image/jpeg",
                            headers={
                                "Access-Control-Allow-Origin": "*",
                                "Cache-Control": "public, max-age=86400"
                            }
                        )
                    url_target = res.get("url") or res.get("avatar_url") or res.get("profile_pic_url") or res.get("profile_url") or res.get("avatar")
                    if url_target and str(url_target).startswith("http"):
                        return RedirectResponse(
                            url_target,
                            status_code=302,
                            headers={
                                "Access-Control-Allow-Origin": "*",
                                "Cache-Control": "public, max-age=86400"
                            }
                        )
            except Exception:
                continue

    except Exception as e:
        print(f"[ROOT-AVATAR-PROXY] Erro ao buscar avatar para jid={jid}: {e}", flush=True)

    raise HTTPException(status_code=404, detail="Avatar não encontrado.")


@app.get("/api/whatsapp/sessions/{session_id}/media")
@app.get("/api/v1/whatsapp/sessions/{session_id}/media")
@app.get("/api/sessions/{session_id}/media")
@app.get("/api/crm/media")
@app.get("/api/v1/crm/media")
@app.get("/media")
async def root_media_proxy(
    session_id: Optional[str] = None,
    session: Optional[str] = None,
    messageId: Optional[str] = None,
    message_id: Optional[str] = None
):
    """
    Proxy de mídias (imagem, áudio, vídeo, documentos) consumido pelo frontend.
    Mapeia /api/sessions/{session_id}/media?messageId=...
    """
    target_session = session_id or session
    msg_id = messageId or message_id
    if not msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

    try:
        from app.api.endpoints.whatsapp import make_whatsapp_api_request
        paths_to_try = []
        if target_session and target_session != "default":
            paths_to_try.append(f"/api/sessions/{target_session}/media?messageId={msg_id}")
            paths_to_try.append(f"/media?session={target_session}&messageId={msg_id}")

        paths_to_try.append(f"/media?messageId={msg_id}")
        paths_to_try.append(f"/api/sessions/default/media?messageId={msg_id}")

        for clean_path in paths_to_try:
            try:
                res = await make_whatsapp_api_request("GET", clean_path)
                if isinstance(res, dict):
                    if res.get("_is_binary") and res.get("content"):
                        content_type = res.get("content_type") or "audio/ogg"
                        return Response(
                            content=res["content"],
                            media_type=content_type,
                            headers={
                                "Accept-Ranges": "bytes",
                                "Cache-Control": "private, max-age=604800",
                                "Access-Control-Allow-Origin": "*",
                                "Content-Type": content_type
                            }
                        )
                    url_target = res.get("url") or res.get("media_url") or res.get("media") or res.get("file_url")
                    if url_target and str(url_target).startswith("http"):
                        return RedirectResponse(
                            url_target,
                            status_code=302,
                            headers={
                                "Access-Control-Allow-Origin": "*",
                                "Cache-Control": "private, max-age=604800"
                            }
                        )
            except Exception:
                continue

    except Exception as e:
        print(f"[ROOT-MEDIA-PROXY] Erro ao carregar mídia para msg_id={msg_id}: {e}", flush=True)

    raise HTTPException(status_code=404, detail="Arquivo de mídia não encontrado.")

@app.get("/project/{public_token}")
@limiter.limit("20/minute")
async def serve_project_with_meta(request: Request, public_token: str, db: Session = Depends(get_db)):
    from app.models.project import Project
    project = db.query(Project).filter(Project.public_token == public_token).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    static_dir = os.getenv("STATIC_DIR", "/app/static")
    index_file = os.path.join(static_dir, "index.html")
    
    title = f"Acompanhamento: {project.name}"
    description = f"Portal de acompanhamento do projeto {project.name} ({project.project_type}) para o cliente {project.client_name}. Confira o status e progresso do desenvolvimento."
    
    meta_tags = f"""
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://dominuslabs.online/project/{public_token}">
    <meta property="og:image" content="https://dominuslabs.online/logo.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="https://dominuslabs.online/logo.png">
    """
    
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        if "<head>" in html_content:
            html_content = html_content.replace("<head>", f"<head>{meta_tags}")
        return HTMLResponse(content=html_content)
        
    mock_html = f"<html><head>{meta_tags}</head><body>Welcome to Dominuslabs Project Hub (Dev/Test Mode)</body></html>"
    return HTMLResponse(content=mock_html)

# Serve frontend static files in production (single container deployment)
static_dir = os.getenv("STATIC_DIR", "/app/static")
if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{fallback_path:path}")
    async def spa_fallback(fallback_path: str):
        # Allow standard API router to handle api routes
        if fallback_path.startswith("api") or fallback_path.startswith("docs") or fallback_path.startswith("openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
        
        # Check if requested file exists in static dir (e.g., favicon.ico, logo.png)
        local_file = os.path.join(static_dir, fallback_path)
        if os.path.isfile(local_file):
            return FileResponse(local_file)
            
        # Fallback to index.html for React router SPA routing
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
            
        return {"message": "Welcome to Dominuslabs API"}
else:
    @app.get("/")
    def root():
        return {"message": "Welcome to Dominuslabs API (API-only mode)"}