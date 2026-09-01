"""
Documentação do módulo feedback.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic feedback.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic feedback funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel, Field
from datetime import datetime

class FeedbackBase(BaseModel):
    """
    Classe FeedbackBase.

    O que faz: Representa a estrutura de dados e operações para a entidade FeedbackBase em o esquema de validação Pydantic feedback.
    Impacto na regra de negócio: Centraliza o comportamento da entidade FeedbackBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    final_result: str
    service_rating: str
    invested_value_rating: str
    process_rating: str
    improvements: str
    rating: int = Field(5, ge=1, le=5)

class FeedbackCreate(FeedbackBase):
    """
    Classe FeedbackCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade FeedbackCreate em o esquema de validação Pydantic feedback.
    Impacto na regra de negócio: Centraliza o comportamento da entidade FeedbackCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    project_token: str

class Feedback(FeedbackBase):
    """
    Classe Feedback.

    O que faz: Representa a estrutura de dados e operações para a entidade Feedback em o esquema de validação Pydantic feedback.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Feedback, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: int
    project_id: int
    created_at: datetime

    class Config:
        """
        Classe Config.

        O que faz: Representa a estrutura de dados e operações para a entidade Config em o esquema de validação Pydantic feedback.
        Impacto na regra de negócio: Centraliza o comportamento da entidade Config, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
        """
        from_attributes = True
