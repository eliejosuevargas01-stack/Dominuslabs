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
from app.core.auth import get_current_user, check_project_create_permission, check_project_edit_permission, check_admin_role
from pydantic import BaseModel

class PublicProjectDetail(BaseModel):
    project: Project
    tasks: List[ProjectTask]
    commits: List[CommitLog]
    deploys: List[DeployLog]
    progress: float
    feedback_submitted: bool

    class Config:
        from_attributes = True

router = APIRouter()

@router.get("/", response_model=List[Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return project_repo.get_all(db, skip=skip, limit=limit)

@router.post("/", response_model=Project)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: str = Depends(check_project_create_permission)):
    return project_repo.create(db, obj_in=project_in)

@router.get("/{project_id}", response_model=Project)
def read_project(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=Project)
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db), current_user: str = Depends(check_project_edit_permission)):
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_repo.update(db, db_obj=project, obj_in=project_in)

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(check_admin_role)):
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project_repo.remove(db, id=project_id)
    return {"status": "success", "message": "Project deleted successfully"}

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

    # Check if feedback exists
    from app.models.feedback import Feedback
    fb = db.query(Feedback).filter(Feedback.project_id == project.id).first()
    feedback_submitted = fb is not None

    return {
        "project": project,
        "tasks": tasks,
        "commits": commits,
        "deploys": deploys,
        "progress": progress,
        "feedback_submitted": feedback_submitted
    }

# Tasks
@router.get("/{project_id}/tasks", response_model=List[ProjectTask])
def read_tasks(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return task_repo.get_by_project(db, project_id)

@router.post("/{project_id}/tasks", response_model=ProjectTask)
def create_task(project_id: int, task_in: ProjectTaskCreate, db: Session = Depends(get_db), current_user: str = Depends(check_project_edit_permission)):
    if task_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    return task_repo.create(db, obj_in=task_in)

@router.put("/tasks/{task_id}", response_model=ProjectTask)
def update_task(task_id: int, task_in: ProjectTaskUpdate, db: Session = Depends(get_db), current_user: str = Depends(check_project_edit_permission)):
    from app.models.task import ProjectTask, TaskStatus
    task = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Block undoing tasks completed via GitHub Webhook
    if task.completed_by_github and task_in.status and task_in.status != TaskStatus.DONE:
        raise HTTPException(status_code=400, detail="Tarefas concluídas pelo GitHub não podem ser desfeitas.")
        
    return task_repo.update(db, task_id=task_id, obj_in=task_in)

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

# Public feedback and showcase endpoints
from app.schemas.feedback import FeedbackCreate

class ShowcaseProject(BaseModel):
    name: str
    project_type: str
    status: str

class Testimonial(BaseModel):
    client_name: str
    project_name: str
    project_type: str
    rating: int
    comment: str

class ShowcaseData(BaseModel):
    projects: List[ShowcaseProject]
    testimonials: List[Testimonial]

@router.post("/public/feedback", status_code=201)
def submit_feedback(feedback_in: FeedbackCreate, db: Session = Depends(get_db)):
    project = project_repo.get_by_public_token(db, token=feedback_in.project_token)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models.project import ProjectStatus
    if project.status != ProjectStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Feedback só pode ser enviado para projetos concluídos.")

    from app.models.feedback import Feedback
    existing = db.query(Feedback).filter(Feedback.project_id == project.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Feedback já enviado para este projeto.")

    new_feedback = Feedback(
        project_id=project.id,
        final_result=feedback_in.final_result,
        service_rating=feedback_in.service_rating,
        invested_value_rating=feedback_in.invested_value_rating,
        process_rating=feedback_in.process_rating,
        improvements=feedback_in.improvements,
        rating=feedback_in.rating
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    return {"status": "success", "message": "Feedback enviado com sucesso!"}

@router.get("/public/showcase/data", response_model=ShowcaseData)
def get_public_showcase(db: Session = Depends(get_db)):
    from app.models.project import Project
    all_projects = db.query(Project).all()
    
    projects_list = []
    for p in all_projects:
        projects_list.append({
            "name": p.name,
            "project_type": p.project_type,
            "status": p.status.value
        })
        
    from app.models.feedback import Feedback
    feedbacks = db.query(Feedback).join(Project).all()
    
    testimonials_list = []
    for f in feedbacks:
        testimonials_list.append({
            "client_name": f.project.client_name,
            "project_name": f.project.name,
            "project_type": f.project.project_type,
            "rating": f.rating,
            "comment": f.final_result
        })
        
    return {
        "projects": projects_list,
        "testimonials": testimonials_list
    }