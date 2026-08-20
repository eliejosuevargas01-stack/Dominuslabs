from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user, check_crm_permission
from app.models.user import User
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.whatsapp_service import get_tenant_id_for_user

router = APIRouter()

@router.get("", response_model=List[ProductResponse])
async def get_products(
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    products = db.query(Product).filter(Product.tenant_id == tenant_id).all()
    return products

@router.post("", response_model=ProductResponse)
async def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    
    new_product = Product(
        id=f"item-{uuid.uuid4().hex[:8]}",
        tenant_id=tenant_id,
        name=product_in.name,
        category=product_in.category,
        price=product_in.price,
        description=product_in.description,
        available=product_in.available,
        image_url=product_in.image_url
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    
    product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    update_data = product_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
        
    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    
    product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    db.delete(product)
    db.commit()
    return {"ok": True}
