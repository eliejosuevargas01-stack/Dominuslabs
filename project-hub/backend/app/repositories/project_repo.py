"""
Documentação do módulo project_repo.py.

O que faz: Implementa a lógica estrutural e funcional para o repositório de dados project_repo.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o repositório de dados project_repo funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectRepository:
    """
    Classe ProjectRepository.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectRepository em o repositório de dados project_repo.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectRepository, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    def get(self, db: Session, id: int):
        """
        Função/Método get.

        O que faz: Recuperação de dados cadastrados para get recebendo os parâmetros (db, id) no contexto de o repositório de dados project_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(Project).filter(Project.id == id).first()

    def get_by_public_token(self, db: Session, token: str):
        """
        Função/Método get_by_public_token.

        O que faz: Recuperação de dados cadastrados para get_by_public_token recebendo os parâmetros (db, token) no contexto de o repositório de dados project_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_by_public_token seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(Project).filter(Project.public_token == token).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Função/Método get_all.

        O que faz: Recuperação de dados cadastrados para get_all recebendo os parâmetros (db, skip, limit) no contexto de o repositório de dados project_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_all seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(Project).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ProjectCreate):
        """
        Função/Método create.

        O que faz: Criação de novos registros e processamento para create recebendo os parâmetros (db, obj_in) no contexto de o repositório de dados project_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação create seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        db_obj = Project(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Project, obj_in: ProjectUpdate):
        """
        Função/Método update.

        O que faz: Atualização e modificação de informações para update recebendo os parâmetros (db, db_obj, obj_in) no contexto de o repositório de dados project_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação update seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int):
        """
        Função/Método remove.

        O que faz: Processa remove recebendo os parâmetros (db, id) no contexto de o repositório de dados project_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação remove seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        db_obj = db.query(Project).filter(Project.id == id).first()
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

project_repo = ProjectRepository()