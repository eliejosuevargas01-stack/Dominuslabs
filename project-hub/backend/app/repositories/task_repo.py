from sqlalchemy.orm import Session
from app.models.task import ProjectTask, TaskStatus
from app.schemas.task import ProjectTaskCreate, ProjectTaskUpdate
from datetime import datetime

class TaskRepository:
    def get_by_project(self, db: Session, project_id: int):
        return db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()

    def create(self, db: Session, obj_in: ProjectTaskCreate):
        db_obj = ProjectTask(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, task_id: int, obj_in: ProjectTaskUpdate):
        db_obj = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])

        if update_data.get("status") == TaskStatus.DONE:
            db_obj.completed_at = datetime.utcnow()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

task_repo = TaskRepository()