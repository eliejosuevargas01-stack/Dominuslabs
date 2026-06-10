from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.task import TaskStatus

class ProjectTaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

class ProjectTaskCreate(ProjectTaskBase):
    project_id: int

class ProjectTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class ProjectTask(ProjectTaskBase):
    id: int
    project_id: int
    completed_at: Optional[datetime] = None
    completed_by_github: bool = False

    class Config:
        from_attributes = True