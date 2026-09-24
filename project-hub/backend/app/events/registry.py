"""
SystemEvent Registry — EVT-003

Registro central de tipos de eventos e metadados.
Handlers e routers devem importar deste módulo.
"""

from typing import Dict, List, Optional
from .types import SystemEventType


class EventMetadata:
    """Metadados de um tipo de evento."""
    
    def __init__(
        self,
        event_type: SystemEventType,
        description: str,
        producer: str,
        consumer: str,
        requires_session: bool = True,
    ):
        self.event_type = event_type
        self.description = description
        self.producer = producer
        self.consumer = consumer
        self.requires_session = requires_session


# Registry central de eventos
EVENT_REGISTRY: Dict[SystemEventType, EventMetadata] = {
    SystemEventType.MESSAGE_CREATED: EventMetadata(
        event_type=SystemEventType.MESSAGE_CREATED,
        description="Nova mensagem recebida via WhatsApp",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.MESSAGE_STATUS_UPDATED: EventMetadata(
        event_type=SystemEventType.MESSAGE_STATUS_UPDATED,
        description="Status da mensagem atualizado (enviada/entregue/lida)",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.MESSAGE_REACTION_UPDATED: EventMetadata(
        event_type=SystemEventType.MESSAGE_REACTION_UPDATED,
        description="Reação à mensagem adicionada/removida",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.CONVERSATION_UPDATED: EventMetadata(
        event_type=SystemEventType.CONVERSATION_UPDATED,
        description="Conversa atualizada (novo contato, tag, etc)",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.MEDIA_PROCESSING: EventMetadata(
        event_type=SystemEventType.MEDIA_PROCESSING,
        description="Mídia em processamento",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.MEDIA_READY: EventMetadata(
        event_type=SystemEventType.MEDIA_READY,
        description="Mídia processada e pronta",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.MEDIA_FAILED: EventMetadata(
        event_type=SystemEventType.MEDIA_FAILED,
        description="Falha no processamento de mídia",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.SESSION_CONNECTED: EventMetadata(
        event_type=SystemEventType.SESSION_CONNECTED,
        description="Sessão WhatsApp conectada",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.SESSION_DISCONNECTED: EventMetadata(
        event_type=SystemEventType.SESSION_DISCONNECTED,
        description="Sessão WhatsApp desconectada",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.SESSION_QR_UPDATED: EventMetadata(
        event_type=SystemEventType.SESSION_QR_UPDATED,
        description="QR code da sessão atualizado",
        producer="wa-api",
        consumer="dominus-backend",
        requires_session=True,
    ),
    SystemEventType.ORDER_CREATED: EventMetadata(
        event_type=SystemEventType.ORDER_CREATED,
        description="Novo pedido criado",
        producer="dominus-backend",
        consumer="n8n",
        requires_session=False,
    ),
    SystemEventType.ORDER_UPDATED: EventMetadata(
        event_type=SystemEventType.ORDER_UPDATED,
        description="Pedido atualizado",
        producer="dominus-backend",
        consumer="n8n",
        requires_session=False,
    ),
    SystemEventType.ORDER_CANCELLED: EventMetadata(
        event_type=SystemEventType.ORDER_CANCELLED,
        description="Pedido cancelado",
        producer="dominus-backend",
        consumer="n8n",
        requires_session=False,
    ),
}


def get_event_metadata(event_type: SystemEventType) -> Optional[EventMetadata]:
    """Retorna metadados de um tipo de evento."""
    return EVENT_REGISTRY.get(event_type)


def list_event_types() -> List[SystemEventType]:
    """Lista todos os tipos de eventos registrados."""
    return list(EVENT_REGISTRY.keys())


def get_events_by_producer(producer: str) -> List[SystemEventType]:
    """Lista eventos por producer."""
    return [
        et for et, meta in EVENT_REGISTRY.items()
        if meta.producer == producer
    ]


def get_events_by_consumer(consumer: str) -> List[SystemEventType]:
    """Lista eventos por consumer."""
    return [
        et for et, meta in EVENT_REGISTRY.items()
        if meta.consumer == consumer
    ]
