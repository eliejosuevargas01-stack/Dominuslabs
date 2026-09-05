"""
Documentação do módulo product_media.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para product_media.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para product_media funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import check_crm_permission
from app.models.user import User
from app.models.product_media import ProductMedia
from app.schemas.product_media import ProductMediaResponse

router = APIRouter()

@router.post("/", response_model=ProductMediaResponse)
def upload_product_media(
    product_id: str = Form(...),
    tenant_id: str = Form("default"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_crm_permission)
):
    """
    Função/Método upload_product_media.

    O que faz: Processa upload_product_media recebendo os parâmetros (product_id, tenant_id, file, db, current_user) no contexto de o endpoint de API para product_media.
    Impacto na regra de negócio: Assegura que o fluxo da operação upload_product_media seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    file_type = file.content_type or "application/octet-stream"
    if file_type.startswith("image/"):
        media_type = "image"
    elif file_type.startswith("video/"):
        media_type = "video"
    else:
        raise HTTPException(status_code=400, detail="Only images and videos are supported")

    safe_filename = os.path.basename(file.filename.replace("\\", "/")) if file.filename else ""
    ext = os.path.splitext(safe_filename)[1] if safe_filename else ""
    filename = f"prod_{uuid.uuid4()}{ext}"
    
    folder_path = os.path.join(settings.UPLOAD_DIR, "products")
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, filename)
    
    # URL that the frontend will use to fetch the file via the static uploads endpoint
    relative_url = f"/uploads/products/{filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_media = ProductMedia(
        tenant_id=tenant_id,
        product_id=product_id,
        media_type=media_type,
        media_url=relative_url,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    db.add(db_media)
    db.commit()
    db.refresh(db_media)

    return db_media
