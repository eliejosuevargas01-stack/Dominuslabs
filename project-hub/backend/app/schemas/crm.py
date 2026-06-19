from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class LeadBase(BaseModel):
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
    score: Optional[str] = None
    temperatura: Optional[str] = None
    proposta_inicial: Optional[str] = None
    lid: Optional[str] = None
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
    pass

class LeadUpdate(LeadBase):
    pass

class Lead(LeadBase):
    id: str  # String ID to support flexible N8N systems
    last_interaction: Optional[str] = None
    created_at: Optional[str] = None
    has_messages: Optional[bool] = False
    mensagem_enviada: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True, extra="allow")

class MessageBase(BaseModel):
    sender: str  # "lead" or "user"
    message: str
    channel: Optional[str] = "instagram"
    timestamp: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: Optional[str] = None

class MessageSendPayload(BaseModel):
    lead_id: str
    phone: str
    message: str
    session_id: Optional[str] = None  # sessão WhatsApp a usar; usa preferred_session_id do usuário se None

class CrmDashboardMetrics(BaseModel):
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
