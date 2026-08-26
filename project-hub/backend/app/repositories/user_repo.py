"""
Documentação do módulo user_repo.py.

O que faz: Implementa a lógica estrutural e funcional para o repositório de dados user_repo.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o repositório de dados user_repo funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash

class UserRepository:
    """
    Classe UserRepository.

    O que faz: Representa a estrutura de dados e operações para a entidade UserRepository em o repositório de dados user_repo.
    Impacto na regra de negócio: Centraliza o comportamento da entidade UserRepository, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    def get(self, db: Session, id: int) -> Optional[User]:
        """
        Função/Método get.

        O que faz: Recuperação de dados cadastrados para get recebendo os parâmetros (db, id) no contexto de o repositório de dados user_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(User).filter(User.id == id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        Função/Método get_by_email.

        O que faz: Recuperação de dados cadastrados para get_by_email recebendo os parâmetros (db, email) no contexto de o repositório de dados user_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_by_email seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(User).filter(User.email == email).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Função/Método get_all.

        O que faz: Recuperação de dados cadastrados para get_all recebendo os parâmetros (db, skip, limit) no contexto de o repositório de dados user_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_all seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(User).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: UserCreate) -> User:
        """
        Função/Método create.

        O que faz: Criação de novos registros e processamento para create recebendo os parâmetros (db, obj_in) no contexto de o repositório de dados user_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação create seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        import uuid
        tenant_id = obj_in.tenant_id if obj_in.tenant_id else f"tenant_{uuid.uuid4().hex[:12]}"
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            tenant_id=tenant_id,
            role=obj_in.role,
            permissions=obj_in.permissions
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        """
        Função/Método update.

        O que faz: Atualização e modificação de informações para update recebendo os parâmetros (db, db_obj, obj_in) no contexto de o repositório de dados user_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação update seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
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
        """
        Função/Método remove.

        O que faz: Processa remove recebendo os parâmetros (db, id) no contexto de o repositório de dados user_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação remove seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        db_obj = db.query(User).filter(User.id == id).first()
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

user_repo = UserRepository()
