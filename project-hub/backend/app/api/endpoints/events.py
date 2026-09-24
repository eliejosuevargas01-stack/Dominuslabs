"""
Event Ingress — EVT-004

Endpoint único para ingestão de eventos.
Substitui gradualmente os webhooks antigos (/crm/update-chat, /crm/message-status, etc).
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from app.events.schemas import SystemEvent, EventValidationError, validate_event
from app.events.types import SystemEventType
from app.events.registry import get_event_metadata

router = APIRouter()


class EventIngressResponse(BaseModel):
    """Resposta do ingress de evento."""
    status: str
    event_id: str
    type: str
    received_at: datetime


@router.post("/webhooks/events", response_model=EventIngressResponse)
async def ingest_event(request: Request):
    """
    Endpoint único para ingestão de eventos.
    
    Recebe eventos no formato SystemEvent e enfileira para processamento.
    """
    # Ler payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {e}"
        )
    
    # Validar evento
    try:
        event = validate_event(payload)
    except EventValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event validation failed: {e.errors}"
        )
    
    # Verificar metadados do evento
    metadata = get_event_metadata(event.type)
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown event type: {event.type}"
        )
    
    # TODO: Enfileirar evento para processamento assíncrono
    # Por enquanto, apenas retornar sucesso
    
    return EventIngressResponse(
        status="accepted",
        event_id=event.event_id,
        type=event.type.value,
        received_at=datetime.now(timezone.utc)
    )


@router.post("/webhooks/events/test", response_model=Dict[str, Any])
async def test_event_ingress():
    """
    Endpoint de teste para o Event Ingress.
    Retorna um exemplo de evento válido.
    """
    return {
        "example_event": {
            "version": 1,
            "event_id": str(uuid.uuid4()),
            "type": "message.created",
            "tenant_id": "tenant-123",
            "session_id": "session-456",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "message_id": "msg-789",
                "from": "5511999999999",
                "body": "Exemplo de mensagem",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        },
        "valid_types": [e.value for e in SystemEventType]
    }
