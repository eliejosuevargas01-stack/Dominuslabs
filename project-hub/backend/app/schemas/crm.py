from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class LeadBase(BaseModel):
    company_name: str
    instagram: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = "DISCOVERED"
    origin: Optional[str] = "Outro"
    notes: Optional[str] = None
    proposal: Optional[str] = None
    responsible: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(LeadBase):
    pass

class Lead(LeadBase):
    id: str  # String ID to support flexible N8N systems
    last_interaction: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

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

class CrmDashboardMetrics(BaseModel):
    total_leads: int
    leads_novos: int
    mensagens_enviadas: int
    mensagens_recebidas: int
    respostas_pendentes: int
    propostas_enviadas: int
    negociacoes: int
    clientes_fechados: int
    taxa_conversao: float
