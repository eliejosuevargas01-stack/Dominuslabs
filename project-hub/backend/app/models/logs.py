from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class CommitLog(Base):
    __tablename__ = "commit_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    commit_hash = Column(String)
    message = Column(String)
    author = Column(String)
    commit_date = Column(DateTime)

    project = relationship("Project", back_populates="commits")

class DeployLog(Base):
    __tablename__ = "deploy_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    provider = Column(String) # netlify, vercel
    status = Column(String)
    deploy_url = Column(String, nullable=True)
    deploy_date = Column(DateTime)

    project = relationship("Project", back_populates="deploys")