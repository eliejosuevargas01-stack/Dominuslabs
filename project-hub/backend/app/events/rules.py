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


# ============================================================
# REGRA FUNDAMENTAL DE MENSAGEM — Semântica estrita por tipo
# ============================================================

from typing import Protocol
import logging

logger = logging.getLogger(__name__)


class MessageRepository(Protocol):
    """Interface para repositório de mensagens."""
    
    def find_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Busca mensagem por ID."""
        ...
    
    def create(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria nova mensagem."""
        ...
    
    def update_status(self, message_id: str, status: str) -> Dict[str, Any]:
        """Atualiza status da mensagem."""
        ...
    
    def update_reaction(self, message_id: str, reaction: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza reação da mensagem."""
        ...
    
    def increment_unread(self, conversation_id: str) -> int:
        """Incrementa contador de não lidas."""
        ...
    
    def update_conversation_preview(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Atualiza preview da conversa."""
        ...


class RealtimeEmitter(Protocol):
    """Interface para emissão de eventos realtime."""
    
    def emit_new_message(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Emite evento de nova mensagem."""
        ...
    
    def emit_message_status(self, message_id: str, status: str) -> None:
        """Emite evento de atualização de status."""
        ...
    
    def emit_reaction(self, message_id: str, reaction: Dict[str, Any]) -> None:
        """Emite evento de reação."""
        ...


class NotificationEngine(Protocol):
    """Interface para notificações."""
    
    def notify_new_message(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Notifica nova mensagem (som, browser, etc)."""
        ...


class MessageEventHandler:
    """
    Handler para eventos de mensagem com semântica estrita.
    
    Regra fundamental:
    - created: criação completa (nova mensagem, unread, realtime, notificação)
    - status.updated: apenas atualização de status (NÃO cria, NÃO incrementa unread)
    - reaction.updated: apenas atualização de reação (NÃO cria mensagem normal)
    """
    
    def __init__(
        self,
        repository: MessageRepository,
        realtime: RealtimeEmitter,
        notification: Optional[NotificationEngine] = None,
    ):
        self.repository = repository
        self.realtime = realtime
        self.notification = notification
        self._processed_events: set = set()  # Para idempotência
    
    def handle_message_created(self, event) -> Dict[str, Any]:
        """
        Handler para message.created.
        
        Semântica:
        - Cria nova mensagem no repositório
        - Incrementa unread (se incoming)
        - Atualiza preview da conversa
        - Dispara realtime de nova mensagem
        - Dispara notificação (se configurado)
        """
        # Idempotência
        if event.event_id in self._processed_events:
            logger.info(f"Event {event.event_id} already processed, skipping")
            return {"status": "duplicate", "event_id": event.event_id}
        
        payload = event.payload
        message_id = payload.get("message_id")
        conversation_id = payload.get("conversation_id")
        direction = payload.get("direction", "incoming")  # incoming/outgoing
        
        # Criar mensagem
        message_data = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "tenant_id": event.tenant_id,
            "session_id": event.session_id,
            "direction": direction,
            "body": payload.get("body", ""),
            "timestamp": payload.get("timestamp"),
            "status": "received",
            "created_at": event.occurred_at.isoformat(),
        }
        
        created_message = self.repository.create(message_data)
        
        # Incrementar unread apenas para mensagens incoming
        unread_count = 0
        if direction == "incoming" and conversation_id:
            unread_count = self.repository.increment_unread(conversation_id)
            self.repository.update_conversation_preview(conversation_id, created_message)
        
        # Realtime
        if conversation_id:
            self.realtime.emit_new_message(conversation_id, created_message)
        
        # Notificação (apenas para incoming)
        if direction == "incoming" and self.notification and conversation_id:
            self.notification.notify_new_message(conversation_id, created_message)
        
        self._processed_events.add(event.event_id)
        
        logger.info(
            f"Message created: {message_id} | "
            f"conversation={conversation_id} | "
            f"direction={direction} | "
            f"unread={unread_count}"
        )
        
        return {
            "status": "created",
            "event_id": event.event_id,
            "message_id": message_id,
            "conversation_id": conversation_id,
            "unread_count": unread_count,
        }
    
    def handle_message_status_updated(self, event) -> Dict[str, Any]:
        """
        Handler para message.status.updated.
        
        Semântica:
        - SOMENTE atualiza status de mensagem existente
        - NÃO cria nova mensagem
        - NÃO incrementa unread
        - NÃO dispara notificação de nova mensagem
        """
        payload = event.payload
        message_id = payload.get("message_id")
        new_status = payload.get("status")
        
        # Verificar se mensagem existe
        existing = self.repository.find_by_id(message_id)
        if not existing:
            logger.warning(f"Message {message_id} not found for status update")
            return {
                "status": "error",
                "event_id": event.event_id,
                "error": f"Message {message_id} not found",
            }
        
        # Atualizar status (sem criar nova mensagem)
        updated = self.repository.update_status(message_id, new_status)
        
        # Realtime de status (não de nova mensagem)
        self.realtime.emit_message_status(message_id, new_status)
        
        logger.info(f"Message status updated: {message_id} -> {new_status}")
        
        return {
            "status": "updated",
            "event_id": event.event_id,
            "message_id": message_id,
            "new_status": new_status,
        }
    
    def handle_message_reaction_updated(self, event) -> Dict[str, Any]:
        """
        Handler para message.reaction.updated.
        
        Semântica:
        - SOMENTE atualiza reação
        - NÃO cria nova mensagem normal
        - NÃO incrementa unread (salvo contrato futuro)
        """
        payload = event.payload
        message_id = payload.get("message_id")
        reaction = payload.get("reaction")
        
        # Verificar se mensagem existe
        existing = self.repository.find_by_id(message_id)
        if not existing:
            logger.warning(f"Message {message_id} not found for reaction update")
            return {
                "status": "error",
                "event_id": event.event_id,
                "error": f"Message {message_id} not found",
            }
        
        # Atualizar reação
        updated = self.repository.update_reaction(message_id, reaction)
        
        # Realtime de reação
        self.realtime.emit_reaction(message_id, reaction)
        
        logger.info(f"Message reaction updated: {message_id}")
        
        return {
            "status": "updated",
            "event_id": event.event_id,
            "message_id": message_id,
            "reaction": reaction,
        }
