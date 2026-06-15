from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
import os

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine, get_db

# Import all models to ensure they are registered on Base.metadata
from app.models.project import Project
from app.models.asset import ProjectAsset
from app.models.task import ProjectTask
from app.models.logs import CommitLog, DeployLog

# Create persistent upload folders and database tables
os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "audio"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "documents"), exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

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

@app.get("/project/{public_token}")
async def serve_project_with_meta(public_token: str, db: Session = Depends(get_db)):
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