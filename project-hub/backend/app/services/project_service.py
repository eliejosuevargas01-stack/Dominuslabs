"""
Documentação do módulo project_service.py.

O que faz: Implementa a lógica estrutural e funcional para o serviço de domínio project_service.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o serviço de domínio project_service funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from app.repositories.task_repo import task_repo
from app.models.task import TaskStatus

class ProjectService:
    """
    Classe ProjectService.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectService em o serviço de domínio project_service.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectService, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    @staticmethod
    def calculate_progress(db: Session, project_id: int) -> float:
        """
        Função/Método calculate_progress.

        O que faz: Processa calculate_progress recebendo os parâmetros (db, project_id) no contexto de o serviço de domínio project_service.
        Impacto na regra de negócio: Assegura que o fluxo da operação calculate_progress seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        tasks = task_repo.get_by_project(db, project_id)
# Lógica de decisão (if): Avalia 'if not tasks:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not tasks:
            return 0.0

        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status == TaskStatus.DONE)

        return (completed_tasks / total_tasks) * 100

project_service = ProjectService()