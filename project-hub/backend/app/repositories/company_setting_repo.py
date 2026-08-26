"""
Documentação do módulo company_setting_repo.py.

O que faz: Implementa a lógica estrutural e funcional para o repositório de dados company_setting_repo.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o repositório de dados company_setting_repo funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy.orm import Session
from app.models.company_setting import CompanySetting
from app.schemas.company_setting import CompanySettingUpdate, CompanySettingCreate

class CompanySettingRepository:
    """
    Classe CompanySettingRepository.

    O que faz: Representa a estrutura de dados e operações para a entidade CompanySettingRepository em o repositório de dados company_setting_repo.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CompanySettingRepository, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    def get_by_tenant(self, db: Session, tenant_id: str = "default") -> CompanySetting:
        """
        Função/Método get_by_tenant.

        O que faz: Recuperação de dados cadastrados para get_by_tenant recebendo os parâmetros (db, tenant_id) no contexto de o repositório de dados company_setting_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação get_by_tenant seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        setting = db.query(CompanySetting).filter(CompanySetting.tenant_id == tenant_id).first()
        if not setting:
            # Create a default empty record if none exists for the tenant
            setting = CompanySetting(tenant_id=tenant_id)
            db.add(setting)
            db.commit()
            db.refresh(setting)
        return setting

    def upsert(self, db: Session, obj_in: CompanySettingUpdate, tenant_id: str = "default") -> CompanySetting:
        """
        Função/Método upsert.

        O que faz: Processa upsert recebendo os parâmetros (db, obj_in, tenant_id) no contexto de o repositório de dados company_setting_repo.
        Impacto na regra de negócio: Assegura que o fluxo da operação upsert seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
        setting = db.query(CompanySetting).filter(CompanySetting.tenant_id == tenant_id).first()
        if not setting:
            setting = CompanySetting(tenant_id=tenant_id)
            db.add(setting)
            db.commit()
            db.refresh(setting)

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(setting, field):
                setattr(setting, field, value)

        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

company_setting_repo = CompanySettingRepository()
