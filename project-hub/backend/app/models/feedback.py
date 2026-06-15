from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True)
    final_result = Column(String)
    service_rating = Column(String)
    invested_value_rating = Column(String)
    process_rating = Column(String)
    improvements = Column(String)
    rating = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
