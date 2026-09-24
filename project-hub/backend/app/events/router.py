"""
Event Router — EVT-005

Roteador de eventos: recebe eventos do Event Ingress e despacha
para os handlers apropriados baseado no tipo de evento.
"""

from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
import logging

from .schemas import SystemEvent
from .types import SystemEventType

logger = logging.getLogger(__name__)


@dataclass
class EventHandlerResult:
    """Resultado do processamento de um evento."""
    success: bool
    event_id: str
    handler: str
    error: Optional[str] = None


class EventRouter:
    """
    Roteador central de eventos.
    
    Recebe eventos validados e despacha para handlers registrados.
    """
    
    def __init__(self):
        self._handlers: Dict[SystemEventType, Callable] = {}
    
    def register_handler(
        self,
        event_type: SystemEventType,
        handler: Callable[[SystemEvent], EventHandlerResult]
    ) -> None:
        """
        Registra um handler para um tipo de evento.
        
        Args:
            event_type: Tipo de evento canônico
            handler: Função que processa o evento
        """
        if event_type in self._handlers:
            logger.warning(f"Overwriting handler for {event_type}")
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type}")
    
    def route(self, event: SystemEvent) -> EventHandlerResult:
        """
        Roteia um evento para o handler apropriado.
        
        Args:
            event: Evento validado (SystemEvent)
            
        Returns:
            EventHandlerResult com resultado do processamento
            
        Raises:
            UNHANDLED_EVENT_TYPE: Se não houver handler registrado para o tipo
        """
        handler = self._handlers.get(event.type)
        
        if handler is None:
            # SEM fallback — erro explícito para tipo sem handler
            logger.error(
                f"UNHANDLED_EVENT_TYPE: {event.type} | "
                f"event_id={event.event_id} | "
                f"tenant_id={event.tenant_id} | "
                f"session_id={event.session_id}"
            )
            return EventHandlerResult(
                success=False,
                event_id=event.event_id,
                handler="none",
                error=f"UNHANDLED_EVENT_TYPE: {event.type}"
            )
        
        try:
            result = handler(event)
            logger.info(f"Event {event.event_id} ({event.type}) processed by {handler.__name__}")
            return result
        except Exception as e:
            logger.exception(f"Error processing event {event.event_id}")
            return EventHandlerResult(
                success=False,
                event_id=event.event_id,
                handler=handler.__name__,
                error=str(e)
            )
    
    def list_handlers(self) -> Dict[str, str]:
        """Lista todos os handlers registrados."""
        return {
            et.value: handler.__name__
            for et, handler in self._handlers.items()
        }


# Instância global do router
event_router = EventRouter()


# Handlers padrão (placeholders para implementação futura)
# NOTA: MessageEventHandler requer injeção de dependências (repository, realtime, notification)
# Será integrado quando o repositório real estiver disponível

def handle_message_created(event: SystemEvent) -> EventHandlerResult:
    """Handler para message.created."""
    # TODO: Integrar com MessageEventHandler quando repositório estiver disponível
    return EventHandlerResult(
        success=True,
        event_id=event.event_id,
        handler="handle_message_created"
    )


def handle_message_status_updated(event: SystemEvent) -> EventHandlerResult:
    """Handler para message.status.updated."""
    # TODO: Integrar com MessageEventHandler quando repositório estiver disponível
    return EventHandlerResult(
        success=True,
        event_id=event.event_id,
        handler="handle_message_status_updated"
    )


def handle_message_reaction_updated(event: SystemEvent) -> EventHandlerResult:
    """Handler para message.reaction.updated."""
    # TODO: Integrar com MessageEventHandler quando repositório estiver disponível
    return EventHandlerResult(
        success=True,
        event_id=event.event_id,
        handler="handle_message_reaction_updated"
    )


def handle_session_connected(event: SystemEvent) -> EventHandlerResult:
    """Handler para session.connected."""
    # TODO: Implementar lógica de negócio
    return EventHandlerResult(
        success=True,
        event_id=event.event_id,
        handler="handle_session_connected"
    )


def handle_session_disconnected(event: SystemEvent) -> EventHandlerResult:
    """Handler para session.disconnected."""
    # TODO: Implementar lógica de negócio
    return EventHandlerResult(
        success=True,
        event_id=event.event_id,
        handler="handle_session_disconnected"
    )


def handle_session_qr_updated(event: SystemEvent) -> EventHandlerResult:
    """Handler para session.qr.updated."""
    # TODO: Implementar lógica de negócio
    return EventHandlerResult(
        success=True,
        event_id=event.event_id,
        handler="handle_session_qr_updated"
    )


# Registrar handlers padrão
event_router.register_handler(SystemEventType.MESSAGE_CREATED, handle_message_created)
event_router.register_handler(SystemEventType.MESSAGE_STATUS_UPDATED, handle_message_status_updated)
event_router.register_handler(SystemEventType.MESSAGE_REACTION_UPDATED, handle_message_reaction_updated)
event_router.register_handler(SystemEventType.SESSION_CONNECTED, handle_session_connected)
event_router.register_handler(SystemEventType.SESSION_DISCONNECTED, handle_session_disconnected)
event_router.register_handler(SystemEventType.SESSION_QR_UPDATED, handle_session_qr_updated)
