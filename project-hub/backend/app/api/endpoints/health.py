from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()

@router.get("/")
def health_check():
    return {"status": "ok"}

@router.get("/migrate-products")
def migrate_products(db: Session = Depends(get_db)):
    from app.models.product import Product
    import uuid
    import json
    
    count = 0
    try:
        result = db.execute(text("SELECT tenant_id, menu_catalog FROM company_settings WHERE menu_catalog IS NOT NULL"))
        for row in result:
            tenant_id = row[0]
            menu_catalog = row[1]
            if isinstance(menu_catalog, str):
                menu_catalog = json.loads(menu_catalog)
                
            if isinstance(menu_catalog, list):
                for item in menu_catalog:
                    p = Product(
                        id=item.get("id", f"item-{uuid.uuid4().hex[:8]}"),
                        tenant_id=tenant_id,
                        name=item.get("name", "Sem Nome"),
                        category=item.get("category"),
                        price=item.get("price", 0.0),
                        description=item.get("description"),
                        available=item.get("available", True),
                        image_url=item.get("image_url")
                    )
                    db.merge(p)  # merge in case ID already exists
                    count += 1
        db.commit()
    except Exception as e:
        db.rollback()
        print("Migration error:", e)
        return {"error": str(e)}
        
    try:
        db.execute(text("ALTER TABLE company_settings DROP COLUMN menu_catalog"))
        db.commit()
    except Exception as e:
        db.rollback()
        print("Could not drop column:", e)
        
    return {"migrated": count, "message": "Migration completed"}
