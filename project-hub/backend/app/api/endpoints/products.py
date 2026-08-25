"""
Documentação do módulo products.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para products.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para products funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import re

from app.core.database import get_db
from app.core.auth import get_current_user, check_crm_permission
from app.models.user import User
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.whatsapp_service import get_tenant_id_for_user

router = APIRouter()

def generate_slug(name: str) -> str:
    """
    Função/Método generate_slug.

    O que faz: Processa generate_slug recebendo os parâmetros (name) no contexto de o endpoint de API para products.
    Impacto na regra de negócio: Assegura que o fluxo da operação generate_slug seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

def _serialize_product(p: Product) -> dict:
    """
    Função/Método _serialize_product.

    O que faz: Processa _serialize_product recebendo os parâmetros (p) no contexto de o endpoint de API para products.
    Impacto na regra de negócio: Assegura que o fluxo da operação _serialize_product seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return {
        "id": str(p.id),
        "tenant_id": p.tenant_id,
        "name": p.nome,
        "category": p.categoria,
        "price": float(p.preco) if p.preco else 0.0,
        "description": p.descricao,
        "available": p.disponivel,
        "image_url": p.imagem_url,
        "stock": getattr(p, 'estoque', 0),
        "created_at": p.created_at
    }

@router.get("", response_model=List[ProductResponse])
async def get_products(
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Função/Método get_products.

    O que faz: Recuperação de dados cadastrados para get_products recebendo os parâmetros (db, current_user) no contexto de o endpoint de API para products.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_products seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    db_products = db.query(Product).filter(Product.tenant_id == tenant_id).all()
    return [_serialize_product(p) for p in db_products]

@router.post("", response_model=ProductResponse)
async def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Função/Método create_product.

    O que faz: Criação de novos registros e processamento para create_product recebendo os parâmetros (product_in, db, current_user) no contexto de o endpoint de API para products.
    Impacto na regra de negócio: Assegura que o fluxo da operação create_product seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    
    new_product = Product(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        nome=product_in.name,
        codigo_slug=generate_slug(product_in.name),
        categoria=product_in.category,
        preco=product_in.price,
        descricao=product_in.description,
        disponivel=product_in.available,
        imagem_url=product_in.image_url,
        estoque=getattr(product_in, 'stock', 0)
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return _serialize_product(new_product)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Função/Método update_product.

    O que faz: Atualização e modificação de informações para update_product recebendo os parâmetros (product_id, product_in, db, current_user) no contexto de o endpoint de API para products.
    Impacto na regra de negócio: Assegura que o fluxo da operação update_product seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    
    product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
# Lógica de decisão (if): Avalia 'if not product:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
# Lógica de decisão (if): Avalia 'if product_in.name is not None...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if product_in.name is not None: 
        product.nome = product_in.name
        product.codigo_slug = generate_slug(product_in.name)
# Lógica de decisão (if): Avalia 'if product_in.category is not ...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if product_in.category is not None: product.categoria = product_in.category
# Lógica de decisão (if): Avalia 'if product_in.price is not Non...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if product_in.price is not None: product.preco = product_in.price
# Lógica de decisão (if): Avalia 'if product_in.description is n...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if product_in.description is not None: product.descricao = product_in.description
# Lógica de decisão (if): Avalia 'if product_in.available is not...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if product_in.available is not None: product.disponivel = product_in.available
# Lógica de decisão (if): Avalia 'if product_in.image_url is not...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if product_in.image_url is not None: product.imagem_url = product_in.image_url
# Lógica de decisão (if): Avalia 'if hasattr(product_in, 'stock'...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if hasattr(product_in, 'stock') and product_in.stock is not None: product.estoque = product_in.stock
        
    db.commit()
    db.refresh(product)
    return _serialize_product(product)

@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_crm_permission)
):
    """
    Função/Método delete_product.

    O que faz: Remoção segura e exclusão lógica/física para delete_product recebendo os parâmetros (product_id, db, current_user) no contexto de o endpoint de API para products.
    Impacto na regra de negócio: Assegura que o fluxo da operação delete_product seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    user = db.query(User).filter(User.email == current_user).first()
    tenant_id = await get_tenant_id_for_user(user, db)
    
    product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
# Lógica de decisão (if): Avalia 'if not product:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    db.delete(product)
    db.commit()
    return {"ok": True}
