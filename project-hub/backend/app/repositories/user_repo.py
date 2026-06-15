from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash

class UserRepository:
    def get(self, db: Session, id: int) -> Optional[User]:
        return db.query(User).filter(User.id == id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            role=obj_in.role,
            can_create_projects=obj_in.can_create_projects,
            can_edit_projects=obj_in.can_edit_projects,
            can_manage_crm=obj_in.can_manage_crm,
            can_use_scrapper=obj_in.can_use_scrapper
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Hash password if updated
        if "password" in update_data and update_data["password"]:
            db_obj.hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            
        for field in update_data:
            setattr(db_obj, field, update_data[field])
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> Optional[User]:
        db_obj = db.query(User).filter(User.id == id).first()
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

user_repo = UserRepository()
