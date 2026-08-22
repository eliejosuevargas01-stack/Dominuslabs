from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class CommitLogBase(BaseModel):
    commit_hash: str
    message: str
    author: str
    commit_date: datetime

class CommitLogCreate(CommitLogBase):
    project_id: int

class CommitLog(CommitLogBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True

class DeployLogBase(BaseModel):
    provider: str
    status: str
    deploy_url: Optional[HttpUrl] = None
    deploy_date: datetime

class DeployLogCreate(DeployLogBase):
    project_id: int

class DeployLog(DeployLogBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True