"""
Documentação do módulo asset_repo.py.

O que faz: Implementa a lógica estrutural e funcional para o repositório de dados asset_repo.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o repositório de dados asset_repo funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from app.models.asset import ProjectAsset
from app.schemas.asset import ProjectAssetCreate

class AssetRepository:
    """
    Classe AssetRepository.

    O que faz: Representa a estrutura de dados e operações para a entidade AssetRepository em o repositório de dados asset_repo.
    Impacto na regra de negócio: Centraliza o comportamento da entidade AssetRepository, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    def get_by_project(self, db: Session, project_id: int, skip: int = 0, limit: int = 100):
        """
        Função/Método get_by_project.

        O que faz: Recuperação de dados cadastrados para get_by_project recebendo os parâmetros (db, project_id, skip, limit) no contexto de o repositório de dados asset_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_by_project seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        return db.query(ProjectAsset).filter(ProjectAsset.project_id == project_id).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ProjectAssetCreate):
        """
        Função/Método create.

        O que faz: Criação de novos registros e processamento para create recebendo os parâmetros (db, obj_in) no contexto de o repositório de dados asset_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação create seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        db_obj = ProjectAsset(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

asset_repo = AssetRepository()