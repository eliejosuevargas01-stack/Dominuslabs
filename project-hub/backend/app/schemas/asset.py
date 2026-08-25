"""
Documentação do módulo asset.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic asset.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic asset funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel
from datetime import datetime

class ProjectAssetBase(BaseModel):
    """
    Classe ProjectAssetBase.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectAssetBase em o esquema de validação Pydantic asset.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectAssetBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    file_name: str
    file_type: str
    file_path: str
    file_size: int

class ProjectAssetCreate(ProjectAssetBase):
    """
    Classe ProjectAssetCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectAssetCreate em o esquema de validação Pydantic asset.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectAssetCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    project_id: int

class ProjectAsset(ProjectAssetBase):
    """
    Classe ProjectAsset.

    O que faz: Representa a estrutura de dados e operações para a entidade ProjectAsset em o esquema de validação Pydantic asset.
    Impacto na regra de negócio: Centraliza o comportamento da entidade ProjectAsset, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    project_id: int
    uploaded_at: datetime

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic asset.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True