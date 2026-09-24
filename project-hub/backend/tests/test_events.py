"""
Testes para EVT-003 — Tipos Canônicos e Schema Endurecido
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.events.schemas import SystemEvent, EventValidationError, validate_event
from app.events.types import SystemEventType


class TestSystemEventType:
    """Testes para SystemEventType enum."""
    
    def test_all_canonical_types_exist(self):
        """Verificar que todos os tipos canônicos existem."""
        expected_types = [
            "message.created",
            "message.status.updated",
            "message.reaction.updated",
            "conversation.updated",
            "media.processing",
            "media.ready",
            "media.failed",
            "session.connected",
            "session.disconnected",
            "session.qr.updated",
            "order.created",
            "order.updated",
            "order.cancelled",
        ]
        for t in expected_types:
            assert SystemEventType.is_valid(t), f"Missing type: {t}"
    
    def test_from_string_valid(self):
        """Conversão de string válida para enum."""
        assert SystemEventType.from_string("message.created") == SystemEventType.MESSAGE_CREATED
        assert SystemEventType.from_string("order.cancelled") == SystemEventType.ORDER_CANCELLED
    
    def test_from_string_invalid(self):
        """Tipo desconhecido rejeitado."""
        with pytest.raises(ValueError, match="Unknown event type"):
            SystemEventType.from_string("invalid.type")
        
        with pytest.raises(ValueError, match="Unknown event type"):
            SystemEventType.from_string("new_message")
    
    def test_enum_serializes_to_canonical_string(self):
        """Enum serializa para string canônica."""
        assert str(SystemEventType.MESSAGE_CREATED) == "message.created"
        assert SystemEventType.MESSAGE_CREATED.value == "message.created"
        assert SystemEventType.ORDER_CANCELLED.value == "order.cancelled"


class TestSystemEventValidation:
    """Testes para validação do schema SystemEvent."""
    
    def test_valid_event_accepted(self):
        """Evento válido é aceito."""
        event = SystemEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            type=SystemEventType.MESSAGE_CREATED,
            tenant_id="tenant-123",
            session_id="session-456",
            occurred_at=datetime.now(timezone.utc),
            payload={"message_id": "msg-789"}
        )
        assert event.type == SystemEventType.MESSAGE_CREATED
        assert event.tenant_id == "tenant-123"
    
    def test_version_1_accepted(self):
        """Versão 1 é aceita."""
        event = SystemEvent(
            version=1,
            event_id="550e8400-e29b-41d4-a716-446655440000",
            type=SystemEventType.MESSAGE_CREATED,
            tenant_id="tenant-123",
            session_id="session-456",
            occurred_at=datetime.now(timezone.utc),
        )
        assert event.version == 1
    
    def test_version_0_rejected(self):
        """Versão 0 é rejeitada."""
        with pytest.raises(ValidationError):
            SystemEvent(
                version=0,
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="tenant-123",
                session_id="session-456",
                occurred_at=datetime.now(timezone.utc),
            )
    
    def test_version_999_rejected(self):
        """Versão 999 é rejeitada."""
        with pytest.raises(ValidationError):
            SystemEvent(
                version=999,
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="tenant-123",
                session_id="session-456",
                occurred_at=datetime.now(timezone.utc),
            )
    
    def test_tenant_id_empty_rejected(self):
        """tenant_id vazio é rejeitado."""
        with pytest.raises(ValidationError, match="tenant_id cannot be empty"):
            SystemEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="",
                session_id="session-456",
                occurred_at=datetime.now(timezone.utc),
            )
    
    def test_tenant_id_whitespace_rejected(self):
        """tenant_id apenas whitespace é rejeitado."""
        with pytest.raises(ValidationError, match="tenant_id cannot be empty"):
            SystemEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="   ",
                session_id="session-456",
                occurred_at=datetime.now(timezone.utc),
            )
    
    def test_session_id_empty_rejected(self):
        """session_id vazio é rejeitado."""
        with pytest.raises(ValidationError, match="session_id cannot be empty"):
            SystemEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="tenant-123",
                session_id="",
                occurred_at=datetime.now(timezone.utc),
            )
    
    def test_event_id_invalid_uuid_rejected(self):
        """event_id não-UUID é rejeitado."""
        with pytest.raises(ValidationError, match="event_id must be a valid UUID"):
            SystemEvent(
                event_id="not-a-uuid",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="tenant-123",
                session_id="session-456",
                occurred_at=datetime.now(timezone.utc),
            )
    
    def test_occurred_at_naive_rejected(self):
        """Timestamp naive é rejeitado."""
        with pytest.raises(ValidationError, match="occurred_at must be timezone-aware"):
            SystemEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="tenant-123",
                session_id="session-456",
                occurred_at=datetime(2026, 9, 24, 2, 0, 0),  # naive
            )
    
    def test_occurred_at_timezone_aware_accepted(self):
        """Timestamp timezone-aware é aceito."""
        event = SystemEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            type=SystemEventType.MESSAGE_CREATED,
            tenant_id="tenant-123",
            session_id="session-456",
            occurred_at=datetime(2026, 9, 24, 2, 0, 0, tzinfo=timezone.utc),
        )
        assert event.occurred_at.tzinfo is not None
    
    def test_occurred_at_iso_string_with_timezone_accepted(self):
        """ISO string com timezone é aceita."""
        event = SystemEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            type=SystemEventType.MESSAGE_CREATED,
            tenant_id="tenant-123",
            session_id="session-456",
            occurred_at="2026-09-24T02:00:00Z",
        )
        assert event.occurred_at.tzinfo is not None
    
    def test_payload_object_accepted(self):
        """Payload dict é aceito."""
        event = SystemEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            type=SystemEventType.MESSAGE_CREATED,
            tenant_id="tenant-123",
            session_id="session-456",
            occurred_at=datetime.now(timezone.utc),
            payload={"message_id": "msg-789", "body": "Hello"}
        )
        assert event.payload["message_id"] == "msg-789"
    
    def test_extra_fields_rejected(self):
        """Campos extras são rejeitados (extra=forbid)."""
        with pytest.raises(ValidationError, match="extra_field"):
            SystemEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="tenant-123",
                session_id="session-456",
                occurred_at=datetime.now(timezone.utc),
                extra_field="not-allowed"
            )
    
    def test_no_default_tenant_created(self):
        """Nenhum tenant default é criado."""
        # Se tentar criar sem tenant_id, deve falhar
        with pytest.raises(ValidationError):
            SystemEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                session_id="session-456",
                occurred_at=datetime.now(timezone.utc),
            )
    
    def test_no_default_session_created(self):
        """Nenhuma session default é criada."""
        with pytest.raises(ValidationError):
            SystemEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                type=SystemEventType.MESSAGE_CREATED,
                tenant_id="tenant-123",
                occurred_at=datetime.now(timezone.utc),
            )


class TestValidateEventFunction:
    """Testes para a função validate_event."""
    
    def test_validate_event_valid(self):
        """Evento válido via validate_event."""
        event = validate_event({
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "type": "message.created",
            "tenant_id": "tenant-123",
            "session_id": "session-456",
            "occurred_at": "2026-09-24T02:00:00Z",
            "payload": {"message_id": "msg-789"}
        })
        assert event.type == SystemEventType.MESSAGE_CREATED
    
    def test_validate_event_missing_field(self):
        """Campo obrigatório faltando."""
        with pytest.raises(EventValidationError, match="Missing required field"):
            validate_event({
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "message.created",
                # tenant_id faltando
                "session_id": "session-456",
                "occurred_at": "2026-09-24T02:00:00Z",
            })
    
    def test_validate_event_invalid_type(self):
        """Tipo inválido via validate_event."""
        with pytest.raises(EventValidationError):
            validate_event({
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "invalid.type",
                "tenant_id": "tenant-123",
                "session_id": "session-456",
                "occurred_at": "2026-09-24T02:00:00Z",
            })
