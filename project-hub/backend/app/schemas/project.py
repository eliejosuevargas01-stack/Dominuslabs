from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from app.models.project import ProjectStatus

class ProjectBase(BaseModel):
    name: str
    client_name: str
    description: Optional[str] = None
    project_type: str
    value: float
    status: ProjectStatus = ProjectStatus.NEW
    github_url: Optional[str] = None
    deploy_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    value: Optional[float] = None
    status: Optional[ProjectStatus] = None
    github_url: Optional[str] = None
    deploy_url: Optional[str] = None

class ProjectInDBBase(ProjectBase):
    id: int
    public_token: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    last_commit_message: Optional[str] = None
    last_deploy_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class Project(ProjectInDBBase):
    pass