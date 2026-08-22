from sqlalchemy.orm import Session
from app.models.asset import ProjectAsset
from app.schemas.asset import ProjectAssetCreate

class AssetRepository:
    def get_by_project(self, db: Session, project_id: int):
        return db.query(ProjectAsset).filter(ProjectAsset.project_id == project_id).all()

    def create(self, db: Session, obj_in: ProjectAssetCreate):
        db_obj = ProjectAsset(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

asset_repo = AssetRepository()