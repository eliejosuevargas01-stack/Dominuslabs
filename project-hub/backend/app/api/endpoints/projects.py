"""
Documentação do módulo projects.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para projects.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para projects funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any, Optional

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
    """
    Classe PublicProjectDetail.

    O que faz: Representa a estrutura de dados e operações para a entidade PublicProjectDetail em o endpoint de API para projects.
    Impacto na regra de negócio: Centraliza o comportamento da entidade PublicProjectDetail, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    project: Project
    tasks: List[ProjectTask]
    commits: List[CommitLog]
    deploys: List[DeployLog]
    progress: float
    feedback_submitted: bool

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o endpoint de API para projects.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True

router = APIRouter()

@router.get("/", response_model=List[Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Função/Método read_projects.

    O que faz: Leitura de dados para read_projects recebendo os parâmetros (skip, limit, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação read_projects seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return project_repo.get_all(db, skip=skip, limit=limit)

@router.post("/", response_model=Project)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: str = Depends(check_project_create_permission)):
    """
    Função/Método create_project.

    O que faz: Criação de novos registros e processamento para create_project recebendo os parâmetros (project_in, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação create_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return project_repo.create(db, obj_in=project_in)

@router.get("/{project_id}", response_model=Project)
def read_project(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Função/Método read_project.

    O que faz: Leitura de dados para read_project recebendo os parâmetros (project_id, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação read_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=Project)
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db), current_user: str = Depends(check_project_edit_permission)):
    """
    Função/Método update_project.

    O que faz: Atualização e modificação de informações para update_project recebendo os parâmetros (project_id, project_in, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação update_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    project = project_repo.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_repo.update(db, db_obj=project, obj_in=project_in)

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(check_admin_role)):
    """
    Função/Método delete_project.

    O que faz: Remoção segura e exclusão lógica/física para delete_project recebendo os parâmetros (project_id, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação delete_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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
def read_tasks(project_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Função/Método read_tasks.

    O que faz: Leitura de dados para read_tasks recebendo os parâmetros (project_id, skip, limit, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação read_tasks seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return task_repo.get_by_project(db, project_id, skip=skip, limit=limit)

@router.post("/{project_id}/tasks", response_model=ProjectTask)
def create_task(project_id: int, task_in: ProjectTaskCreate, db: Session = Depends(get_db), current_user: str = Depends(check_project_edit_permission)):
    """
    Função/Método create_task.

    O que faz: Criação de novos registros e processamento para create_task recebendo os parâmetros (project_id, task_in, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação create_task seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    if task_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    return task_repo.create(db, obj_in=task_in)

@router.put("/tasks/{task_id}", response_model=ProjectTask)
def update_task(task_id: int, task_in: ProjectTaskUpdate, db: Session = Depends(get_db), current_user: str = Depends(check_project_edit_permission)):
    """
    Função/Método update_task.

    O que faz: Atualização e modificação de informações para update_task recebendo os parâmetros (task_id, task_in, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação update_task seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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
def read_assets(project_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Função/Método read_assets.

    O que faz: Leitura de dados para read_assets recebendo os parâmetros (project_id, skip, limit, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação read_assets seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return asset_repo.get_by_project(db, project_id, skip=skip, limit=limit)

@router.get("/{project_id}/commits", response_model=List[CommitLog])
def read_commits(project_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Função/Método read_commits.

    O que faz: Leitura de dados para read_commits recebendo os parâmetros (project_id, skip, limit, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação read_commits seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return log_repo.get_commits_by_project(db, project_id, skip=skip, limit=limit)

@router.get("/{project_id}/deploys", response_model=List[DeployLog])
def read_deploys(project_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Função/Método read_deploys.

    O que faz: Leitura de dados para read_deploys recebendo os parâmetros (project_id, skip, limit, db, current_user) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação read_deploys seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return log_repo.get_deploys_by_project(db, project_id, skip=skip, limit=limit)

# Public feedback and showcase endpoints
from app.schemas.feedback import FeedbackCreate

class ShowcaseProject(BaseModel):
    """
    Classe ShowcaseProject.

    O que faz: Representa a estrutura de dados e operações para a entidade ShowcaseProject em o endpoint de API para projects.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ShowcaseProject, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    name: str
    project_type: str
    status: str
    description: Optional[str] = None
    assets: List[ProjectAsset] = []
    deploy_url: Optional[str] = None

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o endpoint de API para projects.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True

class Testimonial(BaseModel):
    """
    Classe Testimonial.

    O que faz: Representa a estrutura de dados e operações para a entidade Testimonial em o endpoint de API para projects.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Testimonial, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    client_name: str
    project_name: str
    project_type: str
    rating: int
    comment: str

class ShowcaseData(BaseModel):
    """
    Classe ShowcaseData.

    O que faz: Representa a estrutura de dados e operações para a entidade ShowcaseData em o endpoint de API para projects.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ShowcaseData, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    projects: List[ShowcaseProject]
    testimonials: List[Testimonial]

@router.post("/public/feedback", status_code=201)
def submit_feedback(feedback_in: FeedbackCreate, db: Session = Depends(get_db)):
    """
    Função/Método submit_feedback.

    O que faz: Processa submit_feedback recebendo os parâmetros (feedback_in, db) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação submit_feedback seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
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
    """
    Função/Método get_public_showcase.

    O que faz: Recuperação de dados cadastrados para get_public_showcase recebendo os parâmetros (db) no contexto de o endpoint de API para projects.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_public_showcase seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    from app.models.project import Project
    all_projects = db.query(Project).options(joinedload(Project.assets)).all()
    
    projects_list = []
    for p in all_projects:
        # Filter assets to include only images and videos for safety/portfolio relevance
        filtered_assets = [a for a in p.assets if a.file_type in ("images", "videos")]
        projects_list.append({
            "name": p.name,
            "project_type": p.project_type,
            "status": p.status.value,
            "description": p.description,
            "assets": filtered_assets,
            "deploy_url": p.deploy_url
        })
        
    from app.models.feedback import Feedback
    feedbacks = db.query(Feedback).options(joinedload(Feedback.project)).all()
    
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