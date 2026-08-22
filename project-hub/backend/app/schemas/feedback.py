from pydantic import BaseModel, Field
from datetime import datetime

class FeedbackBase(BaseModel):
    final_result: str
    service_rating: str
    invested_value_rating: str
    process_rating: str
    improvements: str
    rating: int = Field(5, ge=1, le=5)

class FeedbackCreate(FeedbackBase):
    project_token: str

class Feedback(FeedbackBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True
