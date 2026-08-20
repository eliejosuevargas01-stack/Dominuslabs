import os
import sys
import uuid
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.database import Base, engine
from app.models.company_setting import CompanySetting
from app.models.product import Product

def migrate():
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    settings = db.query(CompanySetting).all()
    count = 0
    for s in settings:
        if s.menu_catalog and isinstance(s.menu_catalog, list):
            for item in s.menu_catalog:
                # create product
                p = Product(
                    id=item.get("id", f"item-{uuid.uuid4().hex[:8]}"),
                    tenant_id=s.tenant_id,
                    name=item.get("name", "Sem Nome"),
                    category=item.get("category"),
                    price=item.get("price", 0.0),
                    description=item.get("description"),
                    available=item.get("available", True),
                    image_url=item.get("image_url")
                )
                db.add(p)
                count += 1
    
    db.commit()
    db.close()
    print(f"Migrated {count} products!")

if __name__ == "__main__":
    migrate()
