from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.schemas.project import Project, ProjectCreate, ProjectUpdate
from app.schemas.task import ProjectTask, ProjectTaskCreate, ProjectTaskUpdate
from app.schemas.asset import ProjectAsset
from app.schemas.logs import CommitLog, DeployLog
from app.repositories.project_repo import project_repo
from app.repositories.task_repo import task_repo
from app.repositories.asset_repo import asset_repo
from app.repositories.log_repo import log_repo
from app.services.project_service import project_service
from app.core.auth import get_current_user
from pydantic import BaseModel

class PublicProjectDetail(BaseModel):
    project: Project
    tasks: List[ProjectTask]
    commits: List[CommitLog]
    deploys: List[DeployLog]
    progress: float

    class Config:
        from_attributes = True

router = APIRouter()

@router.get("/", response_model=List[Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return project_repo.get_all(db, skip=skip, limit=limit)

@router.post("/", response_model=Project)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return project_repo.create(db, obj_in=project_in)

@router.get("/{project_id}", response_model=Project)
def read_project(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=Project)
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_repo.update(db, db_obj=project, obj_in=project_in)

@router.get("/public/{public_token}", response_model=PublicProjectDetail)
def read_public_project(public_token: str, db: Session = Depends(get_db)):
    """Public access route - no authentication required"""
    project = project_repo.get_by_public_token(db, token=public_token)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Bundle data for public view
    tasks = task_repo.get_by_project(db, project.id)
    commits = log_repo.get_commits_by_project(db, project.id)
    deploys = log_repo.get_deploys_by_project(db, project.id)
    progress = project_service.calculate_progress(db, project.id)

    return {
        "project": project,
        "tasks": tasks,
        "commits": commits,
        "deploys": deploys,
        "progress": progress
    }

# Tasks
@router.get("/{project_id}/tasks", response_model=List[ProjectTask])
def read_tasks(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return task_repo.get_by_project(db, project_id)

@router.post("/{project_id}/tasks", response_model=ProjectTask)
def create_task(project_id: int, task_in: ProjectTaskCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    if task_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    return task_repo.create(db, obj_in=task_in)

@router.put("/tasks/{task_id}", response_model=ProjectTask)
def update_task(task_id: int, task_in: ProjectTaskUpdate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    task = task_repo.update(db, task_id=task_id, obj_in=task_in)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# Additional reads for logs and assets
@router.get("/{project_id}/assets", response_model=List[ProjectAsset])
def read_assets(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return asset_repo.get_by_project(db, project_id)

@router.get("/{project_id}/commits", response_model=List[CommitLog])
def read_commits(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return log_repo.get_commits_by_project(db, project_id)

@router.get("/{project_id}/deploys", response_model=List[DeployLog])
def read_deploys(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return log_repo.get_deploys_by_project(db, project_id)