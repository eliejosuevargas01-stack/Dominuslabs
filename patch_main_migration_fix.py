import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/main.py', 'r') as f:
    content = f.read()

new_migration = """
# Auto-migration
try:
    from app.core.database import SessionLocal, engine
    from sqlalchemy import text
    db = SessionLocal()
    
    is_postgres = engine.name == "postgresql"
    json_default = "'[]'::jsonb" if is_postgres else "'[]'"
    
    statements = [
        'ALTER TABLE company_settings ADD COLUMN niche VARCHAR;',
        "ALTER TABLE company_settings ADD COLUMN delivery_fee_type VARCHAR DEFAULT 'Fixo';",
        'ALTER TABLE company_settings ADD COLUMN delivery_fee_value FLOAT DEFAULT 0;',
        'ALTER TABLE company_settings ADD COLUMN delivery_radius_km FLOAT DEFAULT 0;',
        'ALTER TABLE company_settings ADD COLUMN delivery_max_coverage_km FLOAT DEFAULT 20.0;',
        'ALTER TABLE company_settings ADD COLUMN minimum_order_value FLOAT DEFAULT 0;',
        'ALTER TABLE company_settings ADD COLUMN preparation_time_minutes INTEGER DEFAULT 0;',
        f'ALTER TABLE company_settings ADD COLUMN promotions JSON DEFAULT {json_default};',
    ]
    
    for stmt in statements:
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception:
            db.rollback()
            
    # Add product_media table
    create_table = '''
    CREATE TABLE IF NOT EXISTS product_media (
        id SERIAL PRIMARY KEY,
        tenant_id VARCHAR NOT NULL DEFAULT 'default',
        product_id VARCHAR NOT NULL,
        media_type VARCHAR NOT NULL,
        media_url VARCHAR NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    ''' if is_postgres else '''
    CREATE TABLE IF NOT EXISTS product_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id VARCHAR NOT NULL DEFAULT 'default',
        product_id VARCHAR NOT NULL,
        media_type VARCHAR NOT NULL,
        media_url VARCHAR NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    '''
    try:
        db.execute(text(create_table))
        db.execute(text('CREATE INDEX IF NOT EXISTS ix_product_media_tenant_id ON product_media(tenant_id);'))
        db.execute(text('CREATE INDEX IF NOT EXISTS ix_product_media_product_id ON product_media(product_id);'))
        db.commit()
    except Exception:
        db.rollback()

    db.close()
except Exception as e:
    print(f"Auto-migration failed: {e}")
"""

content = re.sub(r'# Auto-migration for SQLite.*?except Exception as e:\n    print\(f"Auto-migration failed: \{e\}"\)', new_migration.strip(), content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/main.py', 'w') as f:
    f.write(content)

