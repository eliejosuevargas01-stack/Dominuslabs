"""
Documentação do módulo crm.py.

O que faz: Implementa a lógica estrutural e funcional para o esquema de validação Pydantic crm.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o esquema de validação Pydantic crm funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Union
from datetime import datetime

class LeadBase(BaseModel):
    push_name: Optional[str] = None
    nome: Optional[str] = None
    display_phone: Optional[str] = None
    phone: Optional[str] = None
    ultima_mensagem: Optional[str] = None
    created_by: Optional[str] = None
    updated_at: Optional[str] = None

    """
    Classe LeadBase.

    O que faz: Representa a estrutura de dados e operações para a entidade LeadBase em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade LeadBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    lead_id: Optional[str] = None
    empresa_nome: Optional[str] = None
    company_name: Optional[str] = None  # Mantido para compatibilidade
    instagram: Optional[str] = None
    whatsapp: Optional[str] = None     # Mantido para compatibilidade
    telefone_contato: Optional[str] = None
    email_contato: Optional[str] = None
    email: Optional[str] = None        # Mantido para compatibilidade
    status: Optional[str] = "Prospectado"
    origem: Optional[str] = None
    origin: Optional[str] = "Outro"    # Mantido para compatibilidade
    nicho: Optional[str] = None
    segmento: Optional[str] = ""       # Mantido para compatibilidade
    localizacao: Optional[str] = None
    data_coleta: Optional[str] = None
    score: Optional[Union[str, int, float]] = None
    temperatura: Optional[Union[str, int, float]] = None
    proposta_inicial: Optional[str] = None
    lid: Optional[Union[str, int]] = None
    payload: Optional[dict] = None
    notes: Optional[str] = None
    proposal: Optional[str] = None
    responsible: Optional[str] = None
    falha_identificada: Optional[str] = ""
    solucao_recomendada: Optional[str] = ""
    id_anuncio_meta: Optional[str] = None
    alterado_por: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(extra="allow")

class LeadCreate(LeadBase):
    """
    Classe LeadCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade LeadCreate em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade LeadCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    pass

class LeadUpdate(LeadBase):
    """
    Classe LeadUpdate.

    O que faz: Representa a estrutura de dados e operações para a entidade LeadUpdate em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade LeadUpdate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    pass

class Lead(LeadBase):
    """
    Classe Lead.

    O que faz: Representa a estrutura de dados e operações para a entidade Lead em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Lead, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: str  # String ID to support flexible N8N systems
    last_interaction: Optional[str] = None
    created_at: Optional[str] = None
    has_messages: Optional[bool] = False
    mensagem_enviada: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True, extra="allow")

class MessageBase(BaseModel):
    """
    Classe MessageBase.

    O que faz: Representa a estrutura de dados e operações para a entidade MessageBase em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade MessageBase, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    sender: str  # "lead" or "user"
    message: str
    channel: Optional[str] = "instagram"
    timestamp: Optional[str] = None

class MessageCreate(MessageBase):
    """
    Classe MessageCreate.

    O que faz: Representa a estrutura de dados e operações para a entidade MessageCreate em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade MessageCreate, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    pass

class Message(MessageBase):
    """
    Classe Message.

    O que faz: Representa a estrutura de dados e operações para a entidade Message em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade Message, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    id: Optional[str] = None

class MessageSendPayload(BaseModel):
    """
    Classe MessageSendPayload.

    O que faz: Representa a estrutura de dados e operações para a entidade MessageSendPayload em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade MessageSendPayload, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    lead_id: str
    phone: Optional[str] = None
    message: str
    session_id: Optional[str] = None  # sessão WhatsApp a usar; usa preferred_session_id do usuário se None
    contact_jid: Optional[str] = None
    jid: Optional[str] = None

class CrmDashboardMetrics(BaseModel):
    """
    Classe CrmDashboardMetrics.

    O que faz: Representa a estrutura de dados e operações para a entidade CrmDashboardMetrics em o esquema de validação Pydantic crm.
    Impacto na regra de negócio: Centraliza o comportamento da entidade CrmDashboardMetrics, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    total_leads: int
    leads_novos: int
    conversas_iniciadas: int
    mensagens_enviadas: int
    mensagens_recebidas: int
    respostas_pendentes: int
    propostas_enviadas: int
    negociacoes: int
    clientes_fechados: int
    taxa_conversao: float

class Conversation(BaseModel):
    id: Optional[str] = None
    contact_jid: str
    session_id: Optional[str] = None
    unread_count: Optional[int] = 0
    push_name: Optional[str] = None
    name: Optional[str] = None
    ultima_mensagem: Optional[str] = None
    last_interaction: Optional[str] = None
    avatar: Optional[str] = None

class OmnichannelMessage(BaseModel):
    id: Optional[str] = None
    message_id: Optional[str] = None
    sender: Optional[str] = None
    message: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[str] = None
    status: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    caption: Optional[str] = None
