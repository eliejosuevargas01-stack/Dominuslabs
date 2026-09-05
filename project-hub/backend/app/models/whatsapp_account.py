"""
Documentação do módulo whatsapp_account.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados whatsapp_account.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados whatsapp_account funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from app.core.database import Base


class WhatsappAccount(Base):
    """
    Classe WhatsappAccount.

    O que faz: Representa a estrutura de dados e operações para a entidade WhatsappAccount em o modelo de banco de dados whatsapp_account.
    Impacto na regra de negócio: Centraliza o comportamento da entidade WhatsappAccount, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "whatsapp_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(255), index=True, nullable=True)
    idpw = Column(String(255), nullable=True)
    client_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
