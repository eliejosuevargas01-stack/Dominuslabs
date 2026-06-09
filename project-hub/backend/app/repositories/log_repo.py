from sqlalchemy.orm import Session
from app.models.logs import CommitLog, DeployLog
from app.schemas.logs import CommitLogCreate, DeployLogCreate

class LogRepository:
    def create_commit_log(self, db: Session, obj_in: CommitLogCreate):
        db_obj = CommitLog(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_commits_by_project(self, db: Session, project_id: int):
        return db.query(CommitLog).filter(CommitLog.project_id == project_id).order_by(CommitLog.commit_date.desc()).all()

    def create_deploy_log(self, db: Session, obj_in: DeployLogCreate):
        db_obj = DeployLog(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_deploys_by_project(self, db: Session, project_id: int):
        return db.query(DeployLog).filter(DeployLog.project_id == project_id).order_by(DeployLog.deploy_date.desc()).all()

log_repo = LogRepository()