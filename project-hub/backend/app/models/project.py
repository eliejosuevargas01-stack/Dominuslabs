from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
import uuid

from app.core.database import Base

class ProjectStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DEPLOYED = "DEPLOYED"
    DELIVERED = "DELIVERED"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    public_token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    client_name = Column(String)
    description = Column(String, nullable=True)
    project_type = Column(String)
    value = Column(Float)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.NEW)
    github_url = Column(String, nullable=True)
    deploy_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    last_commit_message = Column(String, nullable=True)
    last_deploy_date = Column(DateTime, nullable=True)

    assets = relationship("ProjectAsset", back_populates="project")
    tasks = relationship("ProjectTask", back_populates="project")
    commits = relationship("CommitLog", back_populates="project")
    deploys = relationship("DeployLog", back_populates="project")