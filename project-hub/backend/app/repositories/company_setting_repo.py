from sqlalchemy.orm import Session
from app.models.company_setting import CompanySetting
from app.schemas.company_setting import CompanySettingUpdate, CompanySettingCreate

class CompanySettingRepository:
    def get_by_tenant(self, db: Session, tenant_id: str = "default") -> CompanySetting:
        setting = db.query(CompanySetting).filter(CompanySetting.tenant_id == tenant_id).first()
        if not setting:
            # Create a default empty record if none exists for the tenant
            setting = CompanySetting(tenant_id=tenant_id)
            db.add(setting)
            db.commit()
            db.refresh(setting)
        return setting

    def upsert(self, db: Session, obj_in: CompanySettingUpdate, tenant_id: str = "default") -> CompanySetting:
        setting = db.query(CompanySetting).filter(CompanySetting.tenant_id == tenant_id).first()
        if not setting:
            setting = CompanySetting(tenant_id=tenant_id)
            db.add(setting)
            db.commit()
            db.refresh(setting)

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(setting, field):
                setattr(setting, field, value)

        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

company_setting_repo = CompanySettingRepository()
