from pydantic import BaseModel
from datetime import datetime

class ProjectAssetBase(BaseModel):
    file_name: str
    file_type: str
    file_path: str
    file_size: int

class ProjectAssetCreate(ProjectAssetBase):
    project_id: int

class ProjectAsset(ProjectAssetBase):
    id: int
    project_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True