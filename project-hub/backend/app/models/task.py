from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.core.database import Base

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class ProjectTask(Base):
    __tablename__ = "project_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String)
    description = Column(String, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="tasks")