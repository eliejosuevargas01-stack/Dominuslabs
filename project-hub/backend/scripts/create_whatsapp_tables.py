import psycopg2

# Direct connection string from .env (be cautious with credentials)
conn_str = "postgresql://dominus:RS4k%2Fm@72.60.247.157:5431/postgres"

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            client_id UUID NOT NULL,
            client_secret VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT fk_whatsapp_accounts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_whatsapp_accounts_user_id ON whatsapp_accounts(user_id);
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ whatsapp_accounts table ensured in production DB")
except Exception as e:
    print(f"❌ Error creating table: {e}")
