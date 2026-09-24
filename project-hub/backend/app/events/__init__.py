"""
Events Module — SystemEvent Contract

Este módulo implementa o contrato único de eventos para o Dominus.
Todos os eventos assíncronos seguem o schema SystemEvent.
"""

from .schemas import SystemEvent, EventValidationError, validate_event
from .types import SystemEventType
from .router import event_router, EventRouter, EventHandlerResult

__all__ = [
    "SystemEvent",
    "EventValidationError",
    "validate_event",
    "SystemEventType",
    "event_router",
    "EventRouter",
    "EventHandlerResult",
]
