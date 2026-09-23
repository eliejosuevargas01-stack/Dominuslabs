"""
Documentação do módulo database.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base database.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base database funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

is_sqlite = settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}
if not is_sqlite:
    # Pool sizing otimizado para evitar QueuePool exhaustion
    # - pool_size: conexões persistentes (deve ser >= concurrent DB operations)
    # - max_overflow: burst headroom para picos
    # - pool_timeout: fail fast em vez de esperar 30s bloqueando thread
    # - pool_recycle: reciclar antes do idle timeout do Postgres
    # - pool_use_lifo: permite server-side timeout fechar conexões ociosas
    engine_kwargs["pool_size"] = 20          # De 5 para 20 conexões persistentes
    engine_kwargs["max_overflow"] = 30       # De 10 para 30 overflow (total 50 max)
    engine_kwargs["pool_timeout"] = 10       # De 30 para 10s - fail fast
    engine_kwargs["pool_recycle"] = 1800     # Manter 30min
    engine_kwargs["pool_use_lifo"] = True    # LIFO para melhor reuso

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI, 
    **engine_kwargs
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Função/Método get_db.

    O que faz: Recuperação de dados cadastrados para get_db sem parâmetros específicos no contexto de o módulo core/base database.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_db seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()