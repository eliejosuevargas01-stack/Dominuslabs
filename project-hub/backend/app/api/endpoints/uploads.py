import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.asset import ProjectAsset, ProjectAssetCreate
from app.repositories.asset_repo import asset_repo
from app.repositories.project_repo import project_repo
from app.core.auth import get_current_user, check_project_edit_permission

router = APIRouter()

def get_upload_subfolder(file_type: str) -> str:
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

from fastapi.responses import FileResponse

@router.get("/{subfolder}/{filename}")
def get_uploaded_file(subfolder: str, filename: str):
    file_path = os.path.join(settings.UPLOAD_DIR, subfolder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)