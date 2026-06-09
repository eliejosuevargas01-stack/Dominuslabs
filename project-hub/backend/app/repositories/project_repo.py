from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectRepository:
    def get(self, db: Session, id: int):
        return db.query(Project).filter(Project.id == id).first()

    def get_by_public_token(self, db: Session, token: str):
        return db.query(Project).filter(Project.public_token == token).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Project).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ProjectCreate):
        db_obj = Project(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Project, obj_in: ProjectUpdate):
        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

project_repo = ProjectRepository()