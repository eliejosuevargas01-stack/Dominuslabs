"""
Regra Fundamental de Mensagem — EVT-006

Define a regra fundamental para processamento de mensagens:
toda mensagem deve ter um identificador único e rastreável
desde a origem até o destino final.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


@dataclass
class MessageIdentity:
    """
    Identidade única de uma mensagem no sistema.
    
    Garante rastreabilidade completa desde a origem (WhatsApp)
    até o processamento final (Dominus/n8n).
    """
    
    # Identificador único da mensagem (UUID)
    message_id: str
    
    # ID da mensagem no WhatsApp (pode ser diferente do message_id)
    whatsapp_message_id: Optional[str] = None
    
    # ID da conversa
    conversation_id: Optional[str] = None
    
    # Timestamp de criação da mensagem (timezone-aware)
    created_at: Optional[datetime] = None
    
    # Timestamp de recebimento pelo sistema
    received_at: Optional[datetime] = None
    
    # Metadados adicionais
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.received_at is None:
            self.received_at = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "message_id": self.message_id,
            "whatsapp_message_id": self.whatsapp_message_id,
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageIdentity":
        """Cria a partir de dicionário."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        received_at = None
        if data.get("received_at"):
            received_at = datetime.fromisoformat(data["received_at"])
        
        return cls(
            message_id=data["message_id"],
            whatsapp_message_id=data.get("whatsapp_message_id"),
            conversation_id=data.get("conversation_id"),
            created_at=created_at,
            received_at=received_at,
            metadata=data.get("metadata", {}),
        )


def create_message_identity(
    whatsapp_message_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> MessageIdentity:
    """
    Cria uma nova identidade de mensagem.
    
    Args:
        whatsapp_message_id: ID da mensagem no WhatsApp
        conversation_id: ID da conversa
        metadata: Metadados adicionais
        
    Returns:
        MessageIdentity com ID único gerado
    """
    return MessageIdentity(
        message_id=str(uuid.uuid4()),
        whatsapp_message_id=whatsapp_message_id,
        conversation_id=conversation_id,
        metadata=metadata or {},
    )


def validate_message_identity(identity: MessageIdentity) -> bool:
    """
    Valida uma identidade de mensagem.
    
    Regras:
    - message_id deve ser UUID válido
    - created_at e received_at devem ser timezone-aware
    - whatsapp_message_id pode ser None (para mensagens internas)
    """
    # message_id deve ser UUID
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    import re
    if not re.match(uuid_pattern, identity.message_id, re.IGNORECASE):
        return False
    
    # Timestamps devem ser timezone-aware
    if identity.created_at and identity.created_at.tzinfo is None:
        return False
    if identity.received_at and identity.received_at.tzinfo is None:
        return False
    
    return True
