"""
Documentação do módulo product_media.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para product_media.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para product_media funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import check_product_update_permission, resolve_tenant_from_user
from app.models.user import User
from app.models.product import Product
from app.models.product_media import ProductMedia
from app.schemas.product_media import ProductMediaResponse

router = APIRouter()


def _detect_product_media_format(content: bytes) -> tuple[str, str]:
    """Return the media kind and canonical extension from trusted file bytes."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image", ".jpg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image", ".gif"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image", ".webp"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        major_brand = content[8:12]
        if major_brand in {b"isom", b"iso2", b"avc1", b"mp41", b"mp42", b"M4V ", b"dash"}:
            return "video", ".mp4"

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Formato de mídia não suportado. Envie PNG, JPEG, GIF, WebP ou MP4.",
    )

@router.post("/", response_model=ProductMediaResponse)
def upload_product_media(
    product_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(check_product_update_permission)
):
    """
    Função/Método upload_product_media.

    O que faz: Processa upload_product_media recebendo os parâmetros (product_id, file, db, current_user) no contexto de o endpoint de API para product_media.
    Impacto na regra de negócio: Assegura que o fluxo da operação upload_product_media seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    authorized_tenant_id = resolve_tenant_from_user(user)
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == authorized_tenant_id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    content = file.file.read(settings.PRODUCT_MEDIA_MAX_BYTES + 1)
    if len(content) > settings.PRODUCT_MEDIA_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"A mídia excede o limite de {settings.PRODUCT_MEDIA_MAX_BYTES} bytes.",
        )

    media_type, canonical_extension = _detect_product_media_format(content)
    filename = f"prod_{uuid.uuid4()}{canonical_extension}"
    
    folder_path = os.path.join(settings.UPLOAD_DIR, "products")
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, filename)
    
    # URL that the frontend will use to fetch the file via the static uploads endpoint
    relative_url = f"/uploads/products/{filename}"
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception:
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise

    db_media = ProductMedia(
        tenant_id=authorized_tenant_id,
        product_id=product_id,
        media_type=media_type,
        media_url=relative_url,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )

    product.imagem_url = relative_url
    db.add(db_media)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise
    db.refresh(db_media)

    return db_media
