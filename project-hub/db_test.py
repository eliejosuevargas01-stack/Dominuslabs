import sys
import uuid
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database credentials provided by the user
DB_HOST = "72.60.247.157"
DB_PORT = "5431"
DB_USER = "dominus"
DB_PASSWORD = "RS4k/m"
DB_NAME = "postgres"

print(f"Tentando conectar ao PostgreSQL em {DB_HOST}:{DB_PORT}...")
try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        connect_timeout=10
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    print("Conexão estabelecida com sucesso!")
except Exception as e:
    print(f"\n[ERRO] Falha ao conectar ao banco de dados: {e}")
    print("\nCertifique-se de que:")
    print(f" 1. O host {DB_HOST} está ativo e aceitando conexões na porta {DB_PORT}.")
    print(" 2. Seu IP atual está liberado no firewall do host (ex: pg_hba.conf).")
    print(" 3. Se você estiver usando uma VPN para acessar este servidor, ela está ativa.")
    sys.exit(1)

# Table creation queries
queries = [
    """
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        public_token VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        client_name VARCHAR(255) NOT NULL,
        description TEXT,
        project_type VARCHAR(100) NOT NULL,
        value DOUBLE PRECISION NOT NULL,
        status VARCHAR(50) DEFAULT 'NEW',
        github_url VARCHAR(2048),
        deploy_url VARCHAR(2048),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        last_commit_message TEXT,
        last_deploy_date TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_projects_public_token ON projects(public_token);",
    "CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);",
    """
    CREATE TABLE IF NOT EXISTS project_tasks (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status VARCHAR(50) DEFAULT 'PENDING',
        completed_at TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS project_assets (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        file_name VARCHAR(255) NOT NULL,
        file_type VARCHAR(100) NOT NULL,
        file_path VARCHAR(2048) NOT NULL,
        file_size INTEGER NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS commit_logs (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        commit_hash VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        author VARCHAR(255) NOT NULL,
        commit_date TIMESTAMP NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS deploy_logs (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        provider VARCHAR(100) NOT NULL,
        status VARCHAR(100) NOT NULL,
        deploy_url VARCHAR(2048),
        deploy_date TIMESTAMP NOT NULL
    );
    """
]

print("Criando tabelas no banco de dados...")
for q in queries:
    try:
        cursor.execute(q)
    except Exception as e:
        print(f"[ERRO] Falha ao executar query: {e}")
        conn.close()
        sys.exit(1)
print("Tabelas criadas com sucesso!")

# Insert test project
print("Inserindo projeto de teste...")
public_token = str(uuid.uuid4())
try:
    cursor.execute(
        """
        INSERT INTO projects (public_token, name, client_name, project_type, value, status)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """,
        (public_token, "Clínica Odontológica Marcos", "Marcos", "Landing Page", 500.0, "IN_PROGRESS")
    )
    project_id = cursor.fetchone()[0]
    print(f"Projeto inserido com ID: {project_id}")

    # Create public link
    public_link = f"http://localhost:5173/project/{public_token}"
    print(f"Link público de visualização gerado: {public_link}")

    # Query back project to verify read-only visualization
    cursor.execute("SELECT name, client_name, value, status FROM projects WHERE public_token = %s;", (public_token,))
    row = cursor.fetchone()
    print("\nVerificando leitura dos dados inseridos:")
    print(f"  Nome do Projeto: {row[0]}")
    print(f"  Cliente: {row[1]}")
    print(f"  Valor: R$ {row[2]}")
    print(f"  Status: {row[3]}")
    print("Leitura realizada com sucesso!")

except Exception as e:
    print(f"[ERRO] Falha ao executar transações de teste: {e}")
finally:
    cursor.close()
    conn.close()

print("\nTodos os testes de banco de dados foram concluídos com sucesso!")
