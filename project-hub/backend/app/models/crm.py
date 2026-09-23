"""
Documentação do módulo crm.py.

O que faz: Implementa a lógica estrutural e funcional para o modelo de banco de dados crm.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o modelo de banco de dados crm funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, JSON, PrimaryKeyConstraint
from datetime import datetime, timezone
from app.core.database import Base


class Contact(Base):
    """
    Classe Contact.

    O que faz: Representa a estrutura de dados e operações para a entidade Contact em o modelo de banco de dados crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Contact, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "contacts"

    contact_jid = Column(String, primary_key=True, index=True)
    push_name = Column(String, nullable=True)
    display_phone = Column(String, nullable=True)
    profile_pic_url = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    tenant_id = Column(Text, nullable=True, index=True)


class Conversation(Base):
    """
    Classe Conversation.

    O que faz: Representa a estrutura de dados e operações para a entidade Conversation em o modelo de banco de dados crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Conversation, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "conversations"

    contact_jid = Column(String, primary_key=True, index=True)
    session_id = Column(String, primary_key=True, index=True)
    unread_count = Column(Integer, nullable=True, default=0)
    last_message_preview = Column(Text, nullable=True)
    last_message_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    participant_pushname = Column(String, nullable=True)
    participant = Column(String, nullable=True)
    tenant_id = Column(Text, nullable=True, index=True)


class Message(Base):
    """
    Classe Message.

    O que faz: Representa a estrutura de dados e operações para a entidade Message em o modelo de banco de dados crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Message, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, index=True)
    contact_jid = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    is_from_me = Column(Boolean, nullable=True)
    chat_kind = Column(String, nullable=True)
    message_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    message_timestamp = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    media_url = Column(Text, nullable=True)
    participant = Column(String, nullable=True)
    participant_pushname = Column(String, nullable=True)
    quoted_message_id = Column(String, nullable=True)
    quoted_participant = Column(String, nullable=True)
    quoted_text = Column(Text, nullable=True)
    reaction_text = Column(String, nullable=True)
    reaction_target_message_id = Column(String, nullable=True)
    reaction_target_sender_jid = Column(String, nullable=True)
    tenant_id = Column(Text, nullable=True, index=True)


class Lead(Base):
    """
    Classe Lead.

    O que faz: Representa a estrutura de dados e operações para a entidade Lead em o modelo de banco de dados crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Lead, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    __tablename__ = "leads"

    lead_id = Column(String, primary_key=True, index=True)
    origem = Column(String, nullable=False)
    data_coleta = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    nicho = Column(String, nullable=True)
    status = Column(String, nullable=True)
    empresa_nome = Column(String, nullable=True)
    telefone_contato = Column(String, nullable=True)
    email_contato = Column(String, nullable=True)
    localizacao = Column(Text, nullable=True)
    proposta_inicial = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    temperatura = Column(String, nullable=True)
    payload = Column(JSON, nullable=False)
    lid = Column(String, nullable=True)
    instagram = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    site_quebrado = Column(Boolean, nullable=True)
    diagnostico_tem_cta = Column(Boolean, nullable=True)
    diagnostico_url_abre = Column(Text, nullable=True)
    diagnostico_demora_carregar = Column(Text, nullable=True)
    diagnostico_tem_formulario = Column(Text, nullable=True)
    status_site = Column(String, nullable=True)
    # NO tenant_id column in leads!
