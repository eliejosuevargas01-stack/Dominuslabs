with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/main.py', 'r') as f:
    content = f.read()

migration_code = """
# Auto-migration for SQLite
try:
    from app.core.database import SessionLocal
    import sqlite3
    db = SessionLocal()
    conn = db.get_bind().raw_connection()
    c = conn.cursor()
    
    # 1. Add delivery fields
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_fee_type VARCHAR DEFAULT "Fixo";')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_fee_value FLOAT DEFAULT 0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_radius_km FLOAT DEFAULT 0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN delivery_max_coverage_km FLOAT DEFAULT 20.0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN minimum_order_value FLOAT DEFAULT 0;')
    except Exception: pass
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN preparation_time_minutes INTEGER DEFAULT 0;')
    except Exception: pass
        
    # 2. Add promotions field
    try:
        c.execute('ALTER TABLE company_settings ADD COLUMN promotions JSON DEFAULT "[]";')
    except Exception: pass

    # 3. Add product_media table
    try:
        c.execute('''
        CREATE TABLE IF NOT EXISTS product_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id VARCHAR NOT NULL DEFAULT 'default',
            product_id VARCHAR NOT NULL,
            media_type VARCHAR NOT NULL,
            media_url VARCHAR NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS ix_product_media_tenant_id ON product_media(tenant_id);')
        c.execute('CREATE INDEX IF NOT EXISTS ix_product_media_product_id ON product_media(product_id);')
    except Exception: pass

    conn.commit()
    db.close()
except Exception as e:
    print(f"Auto-migration failed: {e}")
"""

if "# Auto-migration for SQLite" not in content:
    content = content.replace("Base.metadata.create_all(bind=engine)", "Base.metadata.create_all(bind=engine)\n" + migration_code)
    with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/main.py', 'w') as f:
        f.write(content)
    print("Patched main.py successfully.")
