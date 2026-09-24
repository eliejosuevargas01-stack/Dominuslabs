"""
SystemEvent Schema — EVT-002

Contrato versionado para todos os eventos assíncronos do sistema.
Todos os eventos devem seguir este schema para garantir consistência
no pipeline WhatsApp → n8n → Dominus.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SystemEvent(BaseModel):
    """
    Schema base para todos os eventos do sistema.
    
    Campos obrigatórios:
    - version: versão do schema (para migrações futuras)
    - event_id: UUID único do evento (idempotência)
    - type: tipo canônico do evento (ex: message.created)
    - tenant_id: tenant isolado
    - session_id: sessão WhatsApp
    - occurred_at: timestamp ISO-8601
    - payload: dados específicos do evento
    """
    version: int = Field(default=1, description="Schema version")
    event_id: str = Field(..., description="UUID único do evento")
    type: str = Field(..., description="Tipo canônico do evento")
    tenant_id: str = Field(..., description="ID do tenant")
    session_id: str = Field(..., description="ID da sessão WhatsApp")
    occurred_at: datetime = Field(..., description="Timestamp do evento")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dados do evento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "version": 1,
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "message.created",
                "tenant_id": "tenant-123",
                "session_id": "session-456",
                "occurred_at": "2026-09-24T02:00:00Z",
                "payload": {
                    "message_id": "msg-789",
                    "from": "5511999999999",
                    "body": "Olá!",
                    "timestamp": "2026-09-24T01:59:55Z"
                }
            }
        }


class EventValidationError(Exception):
    """Erro de validação de evento."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Event validation failed: {', '.join(errors)}")


def validate_event(event_data: dict) -> SystemEvent:
    """
    Valida um payload de evento contra o schema SystemEvent.
    
    Raises:
        EventValidationError: Se o evento for inválido
    """
    errors = []
    
    # Campos obrigatórios
    required_fields = ["event_id", "type", "tenant_id", "session_id", "occurred_at"]
    for field in required_fields:
        if field not in event_data:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        raise EventValidationError(errors)
    
    # Validar com Pydantic
    try:
        event = SystemEvent(**event_data)
    except Exception as e:
        raise EventValidationError([str(e)])
    
    return event
