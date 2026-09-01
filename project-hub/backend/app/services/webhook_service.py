"""
Documentação do módulo webhook_service.py.

O que faz: Implementa a lógica estrutural e funcional para o serviço de domínio webhook_service.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o serviço de domínio webhook_service funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.schemas.logs import CommitLogCreate, DeployLogCreate
from app.repositories.log_repo import log_repo
from app.repositories.task_repo import task_repo
from app.schemas.task import ProjectTaskUpdate
from app.models.task import TaskStatus

class WebhookService:
    """
    Classe WebhookService.

    O que faz: Representa a estrutura de dados e operações para a entidade WebhookService em o serviço de domínio webhook_service.
    Impacto na regra de negócio: Centraliza o comportamento da entidade WebhookService, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    @staticmethod
    def process_github_webhook(db: Session, project_id: int, commit_hash: str, message: str, author: str, commit_date: datetime):
        """
        Função/Método process_github_webhook.

        O que faz: Processa process_github_webhook recebendo os parâmetros (db, project_id, commit_hash, message, author, commit_date) no contexto de o serviço de domínio webhook_service.
        Impacto na regra de negócio: Assegura que o fluxo da operação process_github_webhook seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        # Create commit log
        log_in = CommitLogCreate(
            project_id=project_id,
            commit_hash=commit_hash,
            message=message,
            author=author,
            commit_date=commit_date
        )
        log_repo.create_commit_log(db, log_in)

        # Auto-check tasks: if commit message matches task name, set status to DONE
        from app.models.task import ProjectTask, TaskStatus
        
        tasks = db.query(ProjectTask).filter(
            ProjectTask.project_id == project_id,
            ProjectTask.status != TaskStatus.DONE
        ).all()
        for task in tasks:
            clean_task = task.name.strip().lower()
            clean_msg = message.strip().lower()
            # Mark task as DONE if commit message matches or contains the task name
            if clean_task == clean_msg or clean_task in clean_msg:
                task.status = TaskStatus.DONE
                task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                task.completed_by_github = True
                db.add(task)
        
        db.commit()

    @staticmethod
    def process_deploy_webhook(db: Session, project_id: int, provider: str, status: str, deploy_url: str, deploy_date: datetime):
        """
        Função/Método process_deploy_webhook.

        O que faz: Processa process_deploy_webhook recebendo os parâmetros (db, project_id, provider, status, deploy_url, deploy_date) no contexto de o serviço de domínio webhook_service.
        Impacto na regra de negócio: Assegura que o fluxo da operação process_deploy_webhook seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        # Create deploy log
        log_in = DeployLogCreate(
            project_id=project_id,
            provider=provider,
            status=status,
            deploy_url=deploy_url,
            deploy_date=deploy_date
        )
        log_repo.create_deploy_log(db, log_in)

webhook_service = WebhookService()