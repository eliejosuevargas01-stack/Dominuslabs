"""
SystemEvent Schema — EVT-002/EVT-003

Contrato versionado para todos os eventos assíncronos do sistema.
Todos os eventos devem seguir este schema para garantir consistência
no pipeline WhatsApp → n8n → Dominus.

EVT-003: Tipos canônicos + validação endurecida
"""

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re

from .types import SystemEventType


class SystemEvent(BaseModel):
    """
    Schema base para todos os eventos do sistema.
    
    Campos obrigatórios:
    - version: versão do schema (apenas 1 aceito atualmente)
    - event_id: UUID único do evento (idempotência)
    - type: tipo canônico do evento (SystemEventType)
    - tenant_id: tenant isolado (não vazio, não whitespace)
    - session_id: sessão WhatsApp (obrigatório para eventos de domínio)
    - occurred_at: timestamp ISO-8601 timezone-aware
    - payload: dados específicos do evento
    """
    version: Literal[1] = Field(default=1, description="Schema version (apenas 1)")
    event_id: str = Field(..., description="UUID único do evento")
    type: SystemEventType = Field(..., description="Tipo canônico do evento")
    tenant_id: str = Field(..., description="ID do tenant")
    session_id: str = Field(..., description="ID da sessão WhatsApp")
    occurred_at: datetime = Field(..., description="Timestamp do evento (timezone-aware)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dados do evento")
    
    model_config = {
        "extra": "forbid",  # Rejeitar campos extras — detectar drift de contrato
        "json_schema_extra": {
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
    }
    
    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Validar tenant_id: não vazio, não apenas whitespace."""
        if not v or not v.strip():
            raise ValueError("tenant_id cannot be empty or whitespace")
        return v.strip()
    
    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validar session_id: não vazio, não apenas whitespace."""
        if not v or not v.strip():
            raise ValueError("session_id cannot be empty or whitespace")
        return v.strip()
    
    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validar event_id: não vazio, formato UUID."""
        if not v or not v.strip():
            raise ValueError("event_id cannot be empty")
        # UUID pattern: 8-4-4-4-12 hex chars
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(v.strip()):
            raise ValueError(f"event_id must be a valid UUID: {v}")
        return v.strip()
    
    @field_validator("occurred_at", mode="before")
    @classmethod
    def validate_occurred_at(cls, v: Any) -> datetime:
        """Validar occurred_at: timezone-aware obrigatório."""
        if isinstance(v, str):
            # Parse ISO string
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        elif isinstance(v, datetime):
            dt = v
        else:
            raise ValueError(f"occurred_at must be datetime or ISO string, got {type(v)}")
        
        # Recusar datetime naive
        if dt.tzinfo is None:
            raise ValueError(
                "occurred_at must be timezone-aware. "
                f"Received naive datetime: {dt.isoformat()}. "
                "Use ISO-8601 with timezone/offset (e.g., 2026-09-24T02:15:00Z or 2026-09-23T23:15:00-03:00)"
            )
        return dt


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
