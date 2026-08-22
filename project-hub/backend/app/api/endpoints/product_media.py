import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.product_media import ProductMedia
from app.schemas.product_media import ProductMediaResponse

router = APIRouter()

@router.post("/", response_model=ProductMediaResponse)
def upload_product_media(
    product_id: str = Form(...),
    tenant_id: str = Form("default"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_type = file.content_type or "application/octet-stream"
    
    if file_type.startswith("image/"):
        media_type = "image"
    elif file_type.startswith("video/"):
        media_type = "video"
    else:
        raise HTTPException(status_code=400, detail="Only images and videos are supported")

    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"prod_{uuid.uuid4()}{ext}"
    
    folder_path = os.path.join(settings.UPLOAD_DIR, "products")
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, filename)
    
    # URL that the frontend will use to fetch the file via the static or get_uploaded_file endpoint
    relative_url = f"/api/uploads/products/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_media = ProductMedia(
        tenant_id=tenant_id,
        product_id=product_id,
        media_type=media_type,
        media_url=relative_url,
        created_at=datetime.utcnow()
    )
    
    db.add(db_media)
    db.commit()
    db.refresh(db_media)

    return db_media
