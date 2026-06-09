from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.logs import CommitLogCreate, DeployLogCreate
from app.repositories.log_repo import log_repo
from app.repositories.task_repo import task_repo
from app.schemas.task import ProjectTaskUpdate
from app.models.task import TaskStatus

class WebhookService:
    @staticmethod
    def process_github_webhook(db: Session, project_id: int, commit_hash: str, message: str, author: str, commit_date: datetime):
        # Create commit log
        log_in = CommitLogCreate(
            project_id=project_id,
            commit_hash=commit_hash,
            message=message,
            author=author,
            commit_date=commit_date
        )
        log_repo.create_commit_log(db, log_in)

        # Future enhancement: Parse message to automatically mark tasks as done.
        # e.g., if message contains "task:hero", find task with name "hero" and update status.
        # This is a stub for that functionality.
        if "task:" in message.lower():
            # Extract task name and find in db to update
            pass

    @staticmethod
    def process_deploy_webhook(db: Session, project_id: int, provider: str, status: str, deploy_url: str, deploy_date: datetime):
        # Create deploy log
        log_in = DeployLogCreate(
            project_id=project_id,
            provider=provider,
            status=status,
            deploy_url=deploy_url,
            deploy_date=deploy_date
        )
        log_repo.create_deploy_log(db, log_in)

webhook_service = WebhookService()