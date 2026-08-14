from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from sqlalchemy.orm import Session
import os

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.middleware import AuditLoggingMiddleware

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
            
            wa_columns = [c["name"] for c in inspector.get_columns("whatsapp_accounts")] if inspector.has_table("whatsapp_accounts") else []
            if "tenant_id" not in wa_columns and inspector.has_table("whatsapp_accounts"):
                conn.execute(text("ALTER TABLE whatsapp_accounts ADD COLUMN tenant_id VARCHAR(255);"))
        print("SQLite migration: users and whatsapp_accounts tenant_id columns checked/added successfully.")
    except Exception as e:
        print(f"SQLite migration warning: {e}")
else:
    # Postgres DDL executions in separate transactions
    ddl_statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_token VARCHAR(255);",
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
                can_create_projects=True,
                can_edit_projects=True,
                can_manage_crm=True,
                can_use_scrapper=True,
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
                can_create_projects=True,
                can_edit_projects=False,
                can_manage_crm=True,
                can_use_scrapper=True,
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

from fastapi.staticfiles import StaticFiles

app.include_router(api_router, prefix=settings.API_V1_STR)

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
        from app.core.mtls_client import get_mtls_async_client
        paths_to_try = []
        if target_session and target_session != "default":
            paths_to_try.append(f"/api/sessions/{target_session}/avatar?jid={jid}&json=true")
            paths_to_try.append(f"/avatar?session={target_session}&jid={jid}&json=true")
            paths_to_try.append(f"/api/sessions/{target_session}/avatar?jid={jid}")
            paths_to_try.append(f"/avatar?session={target_session}&jid={jid}")

        async with get_mtls_async_client(timeout=15.0, service_name="whatsapp") as client:
            base_url = settings.WHATSAPP_API_URL.rstrip("/")
            if base_url.startswith("http://") and ":3000" in base_url:
                base_url = base_url.replace("http://", "https://", 1)

            # Discover active sessions if target_session is missing or default
            try:
                sessions_res = await client.get(f"{base_url}/api/sessions")
                if sessions_res.status_code == 200:
                    sess_data = sessions_res.json()
                    if isinstance(sess_data, list):
                        for s in sess_data:
                            s_id = s.get("name") or s.get("id") or s.get("session_id") or (s.get("session") if isinstance(s.get("session"), str) else None)
                            if s_id and f"/api/sessions/{s_id}/avatar?jid={jid}&json=true" not in paths_to_try:
                                paths_to_try.append(f"/api/sessions/{s_id}/avatar?jid={jid}&json=true")
            except Exception:
                pass

            for clean_path in paths_to_try:
                try:
                    url = f"{base_url}{clean_path}"
                    res = await client.get(url, follow_redirects=True)
                    if res.status_code == 200:
                        content_type = res.headers.get("content-type", "").lower()
                        if "json" in content_type:
                            try:
                                json_data = res.json()
                                url_target = json_data.get("url") or json_data.get("avatar_url") or json_data.get("profile_pic_url") or json_data.get("profile_url") or json_data.get("avatar")
                                if url_target:
                                    return RedirectResponse(
                                        url_target,
                                        status_code=302,
                                        headers={
                                            "Access-Control-Allow-Origin": "*",
                                            "Cache-Control": "public, max-age=86400"
                                        }
                                    )
                            except Exception:
                                pass
                        elif "image" in content_type or len(res.content) > 100:
                            return Response(
                                content=res.content,
                                media_type=content_type or "image/jpeg",
                                headers={
                                    "Access-Control-Allow-Origin": "*",
                                    "Cache-Control": "public, max-age=86400"
                                }
                            )
                except Exception as ex:
                    print(f"[AVATAR-PROXY] Tentativa em {clean_path} falhou: {ex}", flush=True)
                    continue

    except Exception as e:
        print(f"[ROOT-AVATAR-PROXY] Erro ao buscar avatar para jid={jid}: {e}", flush=True)

    raise HTTPException(status_code=404, detail="Avatar não encontrado.")

@app.get("/api/sessions/{session_id}/media")
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
        from app.core.mtls_client import get_mtls_async_client
        paths_to_try = []
        if target_session and target_session != "default":
            paths_to_try.append(f"/api/sessions/{target_session}/media?messageId={msg_id}")

        async with get_mtls_async_client(timeout=30.0, service_name="whatsapp") as client:
            base_url = settings.WHATSAPP_API_URL.rstrip("/")
            if base_url.startswith("http://") and ":3000" in base_url:
                base_url = base_url.replace("http://", "https://", 1)

            # Discover active sessions if target_session is missing or invalid
            try:
                sessions_res = await client.get(f"{base_url}/api/sessions")
                if sessions_res.status_code == 200:
                    sess_data = sessions_res.json()
                    if isinstance(sess_data, list):
                        for s in sess_data:
                            s_id = s.get("name") or s.get("id") or s.get("session_id") or (s.get("session") if isinstance(s.get("session"), str) else None)
                            if s_id and f"/api/sessions/{s_id}/media?messageId={msg_id}" not in paths_to_try:
                                paths_to_try.append(f"/api/sessions/{s_id}/media?messageId={msg_id}")
            except Exception:
                pass

            for clean_path in paths_to_try:
                try:
                    url = f"{base_url}{clean_path}"
                    res = await client.get(url, follow_redirects=True)
                    if res.status_code == 200:
                        content_type = res.headers.get("content-type", "application/octet-stream")
                        # If WhatsApp API returned JSON with a redirect/media URL
                        if "json" in content_type.lower():
                            try:
                                json_data = res.json()
                                url_target = json_data.get("url") or json_data.get("media_url") or json_data.get("media") or json_data.get("file_url")
                                if url_target:
                                    if str(url_target).startswith("http"):
                                        return RedirectResponse(
                                            url_target,
                                            status_code=302,
                                            headers={
                                                "Access-Control-Allow-Origin": "*",
                                                "Cache-Control": "private, max-age=604800"
                                            }
                                        )
                                    else:
                                        res_inner = await client.get(f"{base_url}{url_target}")
                                        if res_inner.status_code == 200:
                                            return Response(
                                                content=res_inner.content,
                                                media_type=res_inner.headers.get("content-type", "audio/ogg"),
                                                headers={
                                                    "Accept-Ranges": "bytes",
                                                    "Cache-Control": "private, max-age=604800",
                                                    "Access-Control-Allow-Origin": "*"
                                                }
                                            )
                            except Exception:
                                pass
                        else:
                            # Direct binary stream (audio/ogg, audio/mp3, image/jpeg, video/mp4, etc.)
                            return Response(
                                content=res.content,
                                media_type=content_type,
                                headers={
                                    "Accept-Ranges": "bytes",
                                    "Cache-Control": "private, max-age=604800",
                                    "Access-Control-Allow-Origin": "*"
                                }
                            )
                except Exception as ex:
                    print(f"[MEDIA-PROXY] Tentativa em {clean_path} falhou: {ex}", flush=True)
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