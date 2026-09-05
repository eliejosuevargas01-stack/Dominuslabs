"""
Documentação do módulo uploads.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para uploads.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para uploads funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
import os
import re
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.asset import ProjectAsset, ProjectAssetCreate
from app.repositories.asset_repo import asset_repo
from app.repositories.project_repo import project_repo
from app.core.auth import get_current_user, check_project_edit_permission

router = APIRouter()

def get_upload_subfolder(file_type: str) -> str:
    """
    Função/Método get_upload_subfolder.

    O que faz: Recuperação de dados cadastrados para get_upload_subfolder recebendo os parâmetros (file_type) no contexto de o endpoint de API para uploads.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_upload_subfolder seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    if file_type.startswith("image/"):
        return "images"
    elif file_type.startswith("video/"):
        return "videos"
    elif file_type.startswith("audio/"):
        return "audio"
    else:
        return "documents"

@router.post("/", response_model=ProjectAsset)
def upload_file(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_project_edit_permission)
):
    """
    Função/Método upload_file.

    O que faz: Processa upload_file recebendo os parâmetros (project_id, file, db, current_user) no contexto de o endpoint de API para uploads.
    Impacto na regra de negócio: Assegura que o fluxo da operação upload_file seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # Check if project exists
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_type = file.content_type or "application/octet-stream"
    subfolder = get_upload_subfolder(file_type)

    # Generate unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"{uuid.uuid4()}{ext}"

    folder_path = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    relative_path = f"uploads/{subfolder}/{filename}"

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    asset_in = ProjectAssetCreate(
        project_id=project_id,
        file_name=file.filename or filename,
        file_type=subfolder,
        file_path=relative_path,
        file_size=file_size
    )

    return asset_repo.create(db, obj_in=asset_in)

@router.get("/{subfolder}/{filename}")
def get_uploaded_file(subfolder: str, filename: str):
    """
    Função/Método get_uploaded_file.

    O que faz: Recuperação de dados cadastrados para get_uploaded_file recebendo os parâmetros (subfolder, filename) no contexto de o endpoint de API para uploads.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_uploaded_file seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", subfolder):
        raise HTTPException(status_code=400, detail="Formato de subpasta inválido")
    if not re.match(r"^[a-zA-Z0-9_.-]+$", filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Formato de arquivo inválido")

    base_dir = os.path.realpath(settings.UPLOAD_DIR)
    target_path = os.path.realpath(os.path.join(base_dir, subfolder, filename))
    if not target_path.startswith(base_dir + os.sep) and target_path != base_dir:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if not os.path.exists(target_path) or not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(target_path)
