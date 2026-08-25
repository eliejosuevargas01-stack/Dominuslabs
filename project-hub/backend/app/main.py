"""
Documentação do módulo main.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base main.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base main funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
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



# Automatic database migration for users and whatsapp_accounts columns
from sqlalchemy import text
db_type = engine.url.drivername
# Lógica de decisão (if): Avalia 'if "sqlite" in db_type:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
if "sqlite" in db_type:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("users")]
# Gerenciador de contexto (with): Garante o gerenciamento seguro de recursos (ex: sessões de banco de dados ou arquivos).
        with engine.begin() as conn:
# Lógica de decisão (if): Avalia 'if "tenant_id" not in columns:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "tenant_id" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tenant_id VARCHAR(255);"))
# Lógica de decisão (if): Avalia 'if "whatsapp_token" not in col...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "whatsapp_token" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN whatsapp_token VARCHAR;"))
# Lógica de decisão (if): Avalia 'if "access_token" not in colum...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "access_token" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN access_token VARCHAR;"))
# Lógica de decisão (if): Avalia 'if "refresh_token" not in colu...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "refresh_token" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN refresh_token VARCHAR;"))
# Lógica de decisão (if): Avalia 'if "token_issued_at" not in co...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "token_issued_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN token_issued_at DATETIME;"))
# Lógica de decisão (if): Avalia 'if "token_expires_at" not in c...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "token_expires_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN token_expires_at DATETIME;"))
            
# Lógica de decisão (if): Avalia 'if "preferred_session_id" not ...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "preferred_session_id" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN preferred_session_id VARCHAR(255);"))
# Lógica de decisão (if): Avalia 'if "permissions" not in column...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if "permissions" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN permissions VARCHAR(255) DEFAULT 'read';"))
            
            wa_columns = [c["name"] for c in inspector.get_columns("whatsapp_accounts")] if inspector.has_table("whatsapp_accounts") else []
# Lógica de decisão (if): Avalia 'if "tenant_id" not in wa_colum...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
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
# Lógica de repetição (for): Itera sobre elementos de 'for stmt in ddl_stat...' processando múltiplos dados em lote para as regras de domínio.
    for stmt in ddl_statements:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
# Gerenciador de contexto (with): Garante o gerenciamento seguro de recursos (ex: sessões de banco de dados ou arquivos).
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception as stmt_err:
            print(f"Postgres migration DDL notice ({stmt}): {stmt_err}")
    print("PostgreSQL migration: users and whatsapp_accounts columns migration completed.")

# Seed database users
def seed_database_users():
    """
    Função/Método seed_database_users.

    O que faz: Processa seed_database_users sem parâmetros específicos no contexto de o módulo core/base main.
    Impacto na regra de negócio: Assegura que o fluxo da operação seed_database_users seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash
    import secrets
    db = SessionLocal()
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        # Seed main admin
        admin_email = settings.ADMIN_USERNAME
# Lógica de decisão (if): Avalia 'if "@" not in admin_email:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "@" not in admin_email:
            admin_email = f"{settings.ADMIN_USERNAME}@dominuslabs.online"
            
        existing_admin = db.query(User).filter(User.email == admin_email).first()
# Lógica de decisão (if): Avalia 'if not existing_admin:...' para validar se o registro já existe para evitar duplicações no banco de dados.
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
# Lógica de decisão (if): Avalia 'if not existing_admin.whatsapp...' para validar se o registro já existe para evitar duplicações no banco de dados.
            if not existing_admin.whatsapp_token:
                existing_admin.whatsapp_token = f"wa_tok_{secrets.token_hex(16)}"
            
        # Seed default viewer / patrik user
        viewer_email = settings.VIEWER_USERNAME
# Lógica de decisão (if): Avalia 'if "@" not in viewer_email:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "@" not in viewer_email:
            viewer_email = "patrik182rodrigues@gmail.com"
            
        existing_viewer = db.query(User).filter(User.email == viewer_email).first()
# Lógica de decisão (if): Avalia 'if not existing_viewer:...' para validar se o registro já existe para evitar duplicações no banco de dados.
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
# Lógica de decisão (if): Avalia 'if not existing_viewer.whatsap...' para validar se o registro já existe para evitar duplicações no banco de dados.
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
# Lógica de decisão (if): Avalia 'if settings.BACKEND_CORS_ORIGI...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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

# Lógica de decisão (if): Avalia 'if os.path.exists(settings.UPL...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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
# Lógica de decisão (if): Avalia 'if not jid:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not jid:
        raise HTTPException(status_code=400, detail="Parâmetro 'jid' é obrigatório.")

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        from app.api.endpoints.whatsapp import make_whatsapp_api_request
        paths_to_try = []
# Lógica de decisão (if): Avalia 'if target_session and target_s...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if target_session and target_session != "default":
            paths_to_try.append(f"/api/sessions/{target_session}/avatar?jid={jid}&json=true")
            paths_to_try.append(f"/avatar?session={target_session}&jid={jid}&json=true")
            paths_to_try.append(f"/api/sessions/{target_session}/avatar?jid={jid}")
            paths_to_try.append(f"/avatar?session={target_session}&jid={jid}")
        paths_to_try.append(f"/avatar?jid={jid}&json=true")
        paths_to_try.append(f"/avatar?jid={jid}")

# Lógica de repetição (for): Itera sobre elementos de 'for clean_path in pa...' processando múltiplos dados em lote para as regras de domínio.
        for clean_path in paths_to_try:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
            try:
                res = await make_whatsapp_api_request("GET", clean_path)
# Lógica de decisão (if): Avalia 'if isinstance(res, dict):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if isinstance(res, dict):
# Lógica de decisão (if): Avalia 'if res.get("_is_binary") and r...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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
# Lógica de decisão (if): Avalia 'if url_target and str(url_targ...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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
# Lógica de decisão (if): Avalia 'if not msg_id:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not msg_id:
        raise HTTPException(status_code=400, detail="Parâmetro 'messageId' é obrigatório.")

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        from app.api.endpoints.whatsapp import make_whatsapp_api_request
        paths_to_try = []
# Lógica de decisão (if): Avalia 'if target_session and target_s...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if target_session and target_session != "default":
            paths_to_try.append(f"/api/sessions/{target_session}/media?messageId={msg_id}")
            paths_to_try.append(f"/media?session={target_session}&messageId={msg_id}")

        paths_to_try.append(f"/media?messageId={msg_id}")
        paths_to_try.append(f"/api/sessions/default/media?messageId={msg_id}")

# Lógica de repetição (for): Itera sobre elementos de 'for clean_path in pa...' processando múltiplos dados em lote para as regras de domínio.
        for clean_path in paths_to_try:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
            try:
                res = await make_whatsapp_api_request("GET", clean_path)
# Lógica de decisão (if): Avalia 'if isinstance(res, dict):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if isinstance(res, dict):
# Lógica de decisão (if): Avalia 'if res.get("_is_binary") and r...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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
# Lógica de decisão (if): Avalia 'if url_target and str(url_targ...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
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
    """
    Função/Método serve_project_with_meta.

    O que faz: Processa serve_project_with_meta recebendo os parâmetros (request, public_token, db) no contexto de o módulo core/base main.
    Impacto na regra de negócio: Assegura que o fluxo da operação serve_project_with_meta seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    from app.models.project import Project
    project = db.query(Project).filter(Project.public_token == public_token).first()
# Lógica de decisão (if): Avalia 'if not project:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
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
    
# Lógica de decisão (if): Avalia 'if os.path.exists(index_file):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if os.path.exists(index_file):
# Gerenciador de contexto (with): Garante o gerenciamento seguro de recursos (ex: sessões de banco de dados ou arquivos).
        with open(index_file, "r", encoding="utf-8") as f:
            html_content = f.read()
# Lógica de decisão (if): Avalia 'if "<head>" in html_content:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if "<head>" in html_content:
            html_content = html_content.replace("<head>", f"<head>{meta_tags}")
        return HTMLResponse(content=html_content)
        
    mock_html = f"<html><head>{meta_tags}</head><body>Welcome to Dominuslabs Project Hub (Dev/Test Mode)</body></html>"
    return HTMLResponse(content=mock_html)

# Serve frontend static files in production (single container deployment)
static_dir = os.getenv("STATIC_DIR", "/app/static")
# Lógica de decisão (if): Avalia 'if os.path.exists(static_dir):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
# Lógica de decisão (if): Avalia 'if os.path.exists(assets_dir):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{fallback_path:path}")
    async def spa_fallback(fallback_path: str):
        """
        Função/Método spa_fallback.

        O que faz: Processa spa_fallback recebendo os parâmetros (fallback_path) no contexto de o módulo core/base main.
        Impacto na regra de negócio: Assegura que o fluxo da operação spa_fallback seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        # Allow standard API router to handle api routes
# Lógica de decisão (if): Avalia 'if fallback_path.startswith("a...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if fallback_path.startswith("api") or fallback_path.startswith("docs") or fallback_path.startswith("openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
        
        # Check if requested file exists in static dir (e.g., favicon.ico, logo.png)
        local_file = os.path.join(static_dir, fallback_path)
# Lógica de decisão (if): Avalia 'if os.path.isfile(local_file):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if os.path.isfile(local_file):
            return FileResponse(local_file)
            
        # Fallback to index.html for React router SPA routing
        index_file = os.path.join(static_dir, "index.html")
# Lógica de decisão (if): Avalia 'if os.path.exists(index_file):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if os.path.exists(index_file):
            return FileResponse(index_file)
            
        return {"message": "Welcome to Dominuslabs API"}
else:
    @app.get("/")
    def root():
        """
        Função/Método root.

        O que faz: Processa root sem parâmetros específicos no contexto de o módulo core/base main.
        Impacto na regra de negócio: Assegura que o fluxo da operação root seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return {"message": "Welcome to Dominuslabs API (API-only mode)"}