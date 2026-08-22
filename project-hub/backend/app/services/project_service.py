from sqlalchemy.orm import Session
from app.repositories.task_repo import task_repo
from app.models.task import TaskStatus

class ProjectService:
    @staticmethod
    def calculate_progress(db: Session, project_id: int) -> float:
        tasks = task_repo.get_by_project(db, project_id)
        if not tasks:
            return 0.0

        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status == TaskStatus.DONE)

        return (completed_tasks / total_tasks) * 100

project_service = ProjectService()