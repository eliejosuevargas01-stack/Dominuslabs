"""
Documentação do módulo task_repo.py.

O que faz: Implementa a lógica estrutural e funcional para o repositório de dados task_repo.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o repositório de dados task_repo funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from app.models.task import ProjectTask, TaskStatus
from app.schemas.task import ProjectTaskCreate, ProjectTaskUpdate
from datetime import datetime, timezone

class TaskRepository:
    """
    Classe TaskRepository.

    O que faz: Representa a estrutura de dados e operações para a entidade TaskRepository em o repositório de dados task_repo.
    Impacto na regra de negócio: Centraliza o comportamento da entidade TaskRepository, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    def get_by_project(self, db: Session, project_id: int, skip: int = 0, limit: int = 100):
        """
        Função/Método get_by_project.

        O que faz: Recuperação de dados cadastrados para get_by_project recebendo os parâmetros (db, project_id, skip, limit) no contexto de o repositório de dados task_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_by_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(ProjectTask).filter(ProjectTask.project_id == project_id).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ProjectTaskCreate):
        """
        Função/Método create.

        O que faz: Criação de novos registros e processamento para create recebendo os parâmetros (db, obj_in) no contexto de o repositório de dados task_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação create seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        db_obj = ProjectTask(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, task_id: int, obj_in: ProjectTaskUpdate):
        """
        Função/Método update.

        O que faz: Atualização e modificação de informações para update recebendo os parâmetros (db, task_id, obj_in) no contexto de o repositório de dados task_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação update seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        db_obj = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        if update_data.get("status") == TaskStatus.DONE:
            db_obj.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

task_repo = TaskRepository()