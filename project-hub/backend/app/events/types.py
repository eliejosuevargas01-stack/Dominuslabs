"""
SystemEvent Types — EVT-003

Tipos canônicos de eventos. Esta é a fonte única de verdade
para todos os tipos de eventos do sistema.

Não adicionar tipos sem:
1. Semântica própria
2. Producer conhecido
3. Consumer conhecido
4. Não duplicar outro evento
5. Documentação no catálogo
"""

from enum import Enum


class SystemEventType(str, Enum):
    """
    Tipos canônicos de eventos do sistema.
    
    Convenção de naming: <domínio>.<ação>
    """
    
    # Mensagens
    MESSAGE_CREATED = "message.created"
    MESSAGE_STATUS_UPDATED = "message.status.updated"
    MESSAGE_REACTION_UPDATED = "message.reaction.updated"
    
    # Conversas
    CONVERSATION_UPDATED = "conversation.updated"
    
    # Mídia
    MEDIA_PROCESSING = "media.processing"
    MEDIA_READY = "media.ready"
    MEDIA_FAILED = "media.failed"
    
    # Sessão WhatsApp
    SESSION_CONNECTED = "session.connected"
    SESSION_DISCONNECTED = "session.disconnected"
    SESSION_QR_UPDATED = "session.qr.updated"
    
    # Pedidos
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_CANCELLED = "order.cancelled"
    
    @classmethod
    def from_string(cls, value: str) -> "SystemEventType":
        """
        Converte string para SystemEventType.
        
        Raises:
            ValueError: Se o tipo não for canônico
        """
        try:
            return cls(value)
        except ValueError:
            valid = [e.value for e in cls]
            raise ValueError(f"Unknown event type: {value}. Valid types: {valid}")
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Verifica se uma string é um tipo canônico válido."""
        return value in cls._value2member_map_
    
    def __str__(self) -> str:
        return self.value
