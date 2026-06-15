from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.auth import check_admin_role
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.repositories.user_repo import user_repo

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_admin_role)
):
    """List all users (Admin only)"""
    return user_repo.get_all(db, skip=skip, limit=limit)

@router.post("/", response_model=UserResponse)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_admin_role)
):
    """Create a new user (Admin only)"""
    existing = user_repo.get_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está sendo utilizado."
        )
    return user_repo.create(db, obj_in=user_in)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_admin_role)
):
    """Update a user details or permissions (Admin only)"""
    user = user_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
        
    if user_in.email and user_in.email != user.email:
        existing = user_repo.get_by_email(db, email=user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está sendo utilizado."
            )
            
    return user_repo.update(db, db_obj=user, obj_in=user_in)

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(check_admin_role)
):
    """Delete a user (Admin only). Prevent deleting oneself."""
    user = user_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
        
    if user.email == current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode excluir o seu próprio usuário."
        )
        
    user_repo.remove(db, id=user_id)
    return {"status": "success", "message": "Usuário excluído com sucesso."}
