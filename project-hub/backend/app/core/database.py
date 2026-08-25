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
# Lógica de decisão (if): Avalia 'if not is_sqlite:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
if not is_sqlite:
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_timeout"] = 30

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
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        yield db
    finally:
        db.close()