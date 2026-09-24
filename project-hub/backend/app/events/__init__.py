"""
Events Module — SystemEvent Contract

Este módulo implementa o contrato único de eventos para o Dominus.
Todos os eventos assíncronos seguem o schema SystemEvent.
"""

from .schemas import SystemEvent, EventValidationError, validate_event

__all__ = ["SystemEvent", "EventValidationError", "validate_event"]
