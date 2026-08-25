"""
Documentação do módulo log_repo.py.

O que faz: Implementa a lógica estrutural e funcional para o repositório de dados log_repo.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o repositório de dados log_repo funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from app.models.logs import CommitLog, DeployLog
from app.schemas.logs import CommitLogCreate, DeployLogCreate

class LogRepository:
    """
    Classe LogRepository.

    O que faz: Representa a estrutura de dados e operações para a entidade LogRepository em o repositório de dados log_repo.
    Impacto na regra de negócio: Centraliza o comportamento da entidade LogRepository, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    def create_commit_log(self, db: Session, obj_in: CommitLogCreate):
        """
        Função/Método create_commit_log.

        O que faz: Criação de novos registros e processamento para create_commit_log recebendo os parâmetros (db, obj_in) no contexto de o repositório de dados log_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação create_commit_log seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        db_obj = CommitLog(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_commits_by_project(self, db: Session, project_id: int, skip: int = 0, limit: int = 100):
        """
        Função/Método get_commits_by_project.

        O que faz: Recuperação de dados cadastrados para get_commits_by_project recebendo os parâmetros (db, project_id, skip, limit) no contexto de o repositório de dados log_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_commits_by_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(CommitLog).filter(CommitLog.project_id == project_id).order_by(CommitLog.commit_date.desc()).offset(skip).limit(limit).all()

    def create_deploy_log(self, db: Session, obj_in: DeployLogCreate):
        """
        Função/Método create_deploy_log.

        O que faz: Criação de novos registros e processamento para create_deploy_log recebendo os parâmetros (db, obj_in) no contexto de o repositório de dados log_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação create_deploy_log seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        dump = obj_in.model_dump()
# Lógica de decisão (if): Avalia 'if dump.get("deploy_url"):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if dump.get("deploy_url"):
            dump["deploy_url"] = str(dump["deploy_url"])
        db_obj = DeployLog(**dump)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_deploys_by_project(self, db: Session, project_id: int, skip: int = 0, limit: int = 100):
        """
        Função/Método get_deploys_by_project.

        O que faz: Recuperação de dados cadastrados para get_deploys_by_project recebendo os parâmetros (db, project_id, skip, limit) no contexto de o repositório de dados log_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_deploys_by_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(DeployLog).filter(DeployLog.project_id == project_id).order_by(DeployLog.deploy_date.desc()).offset(skip).limit(limit).all()

log_repo = LogRepository()