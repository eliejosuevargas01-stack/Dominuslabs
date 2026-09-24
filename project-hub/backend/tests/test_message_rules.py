"""
Testes para EVT-006 — Regra Fundamental de Mensagem

Testa a semântica estrita de cada tipo de evento:
- message.created: criação completa
- message.status.updated: apenas atualização de status
- message.reaction.updated: apenas atualização de reação
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from app.events.rules import (
    MessageEventHandler,
    MessageIdentity,
    create_message_identity,
    validate_message_identity,
)


class TestMessageIdentity:
    """Testes para MessageIdentity."""
    
    def test_create_identity(self):
        """Criação de identidade de mensagem."""
        identity = create_message_identity(
            whatsapp_message_id="wamid.123",
            conversation_id="conv-456",
            metadata={"source": "whatsapp"}
        )
        assert identity.message_id is not None
        assert identity.whatsapp_message_id == "wamid.123"
        assert identity.conversation_id == "conv-456"
        assert identity.created_at is not None and identity.created_at.tzinfo is not None
    
    def test_validate_identity_valid(self):
        """Validação de identidade válida."""
        identity = create_message_identity()
        assert validate_message_identity(identity) is True
    
    def test_validate_identity_invalid_uuid(self):
        """Validação de identidade com UUID inválido."""
        identity = create_message_identity()
        identity.message_id = "not-a-uuid"
        assert validate_message_identity(identity) is False
    
    def test_validate_identity_naive_datetime(self):
        """Validação de identidade com datetime naive."""
        identity = create_message_identity()
        identity.created_at = datetime(2026, 9, 24, 2, 0, 0)  # naive
        assert validate_message_identity(identity) is False


class TestMessageEventHandler:
    """Testes para MessageEventHandler."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock do repositório de mensagens."""
        repo = Mock()
        repo.find_by_id = Mock()
        repo.create = Mock(side_effect=lambda x: {**x, "id": "db-id-123"})
        repo.update_status = Mock(side_effect=lambda mid, status: {"message_id": mid, "status": status})
        repo.update_reaction = Mock(side_effect=lambda mid, r: {"message_id": mid, "reaction": r})
        repo.increment_unread = Mock(return_value=5)
        repo.update_conversation_preview = Mock()
        return repo
    
    @pytest.fixture
    def mock_realtime(self):
        """Mock do emissor realtime."""
        rt = Mock()
        rt.emit_new_message = Mock()
        rt.emit_message_status = Mock()
        rt.emit_reaction = Mock()
        return rt
    
    @pytest.fixture
    def mock_notification(self):
        """Mock do motor de notificação."""
        notif = Mock()
        notif.notify_new_message = Mock()
        return notif
    
    @pytest.fixture
    def handler(self, mock_repository, mock_realtime, mock_notification):
        """Handler com mocks."""
        return MessageEventHandler(mock_repository, mock_realtime, mock_notification)
    
    def create_event(self, event_type, payload, event_id="550e8400-e29b-41d4-a716-446655440000"):
        """Cria evento mock."""
        event = Mock()
        event.event_id = event_id
        event.type = event_type
        event.tenant_id = "tenant-123"
        event.session_id = "session-456"
        event.occurred_at = datetime.now(timezone.utc)
        event.payload = payload
        return event
    
    # ========== message.created ==========
    
    def test_message_created_creates_message(self, handler, mock_repository, mock_realtime, mock_notification):
        """message.created: cria nova mensagem."""
        event = self.create_event("message.created", {
            "message_id": "msg-789",
            "conversation_id": "conv-456",
            "direction": "incoming",
            "body": "Hello",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        result = handler.handle_message_created(event)
        
        assert result["status"] == "created"
        mock_repository.create.assert_called_once()
        mock_repository.increment_unread.assert_called_once_with("conv-456")
        mock_repository.update_conversation_preview.assert_called_once()
        mock_realtime.emit_new_message.assert_called_once()
        mock_notification.notify_new_message.assert_called_once()
    
    def test_message_created_outgoing_no_unread(self, handler, mock_repository, mock_notification):
        """message.created: outgoing não incrementa unread."""
        event = self.create_event("message.created", {
            "message_id": "msg-789",
            "conversation_id": "conv-456",
            "direction": "outgoing",
            "body": "Hello",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        result = handler.handle_message_created(event)
        
        assert result["status"] == "created"
        mock_repository.increment_unread.assert_not_called()
        mock_notification.notify_new_message.assert_not_called()
    
    def test_message_created_idempotent(self, handler, mock_repository):
        """message.created: mesmo event_id não duplica operação."""
        event = self.create_event("message.created", {
            "message_id": "msg-789",
            "conversation_id": "conv-456",
            "direction": "incoming",
            "body": "Hello",
        })
        
        # Primeira vez
        result1 = handler.handle_message_created(event)
        assert result1["status"] == "created"
        assert mock_repository.create.call_count == 1
        
        # Segunda vez (mesmo event_id)
        result2 = handler.handle_message_created(event)
        assert result2["status"] == "duplicate"
        assert mock_repository.create.call_count == 1  # Não chamou novamente
    
    # ========== message.status.updated ==========
    
    def test_message_status_updated_existing_message(self, handler, mock_repository, mock_realtime):
        """message.status.updated: atualiza mensagem existente."""
        mock_repository.find_by_id.return_value = {"message_id": "msg-789", "status": "sent"}
        
        event = self.create_event("message.status.updated", {
            "message_id": "msg-789",
            "status": "read"
        })
        
        result = handler.handle_message_status_updated(event)
        
        assert result["status"] == "updated"
        mock_repository.find_by_id.assert_called_once_with("msg-789")
        mock_repository.update_status.assert_called_once_with("msg-789", "read")
        mock_realtime.emit_message_status.assert_called_once_with("msg-789", "read")
    
    def test_message_status_updated_no_creation(self, handler, mock_repository):
        """message.status.updated: NÃO cria nova mensagem."""
        mock_repository.find_by_id.return_value = {"message_id": "msg-789", "status": "sent"}
        
        event = self.create_event("message.status.updated", {
            "message_id": "msg-789",
            "status": "read"
        })
        
        handler.handle_message_status_updated(event)
        
        mock_repository.create.assert_not_called()
    
    def test_message_status_updated_no_unread_increment(self, handler, mock_repository):
        """message.status.updated: NÃO incrementa unread."""
        mock_repository.find_by_id.return_value = {"message_id": "msg-789", "status": "sent"}
        
        event = self.create_event("message.status.updated", {
            "message_id": "msg-789",
            "status": "read"
        })
        
        handler.handle_message_status_updated(event)
        
        mock_repository.increment_unread.assert_not_called()
    
    def test_message_status_updated_no_new_message_realtime(self, handler, mock_repository, mock_realtime):
        """message.status.updated: NÃO emite new-message realtime."""
        mock_repository.find_by_id.return_value = {"message_id": "msg-789", "status": "sent"}
        
        event = self.create_event("message.status.updated", {
            "message_id": "msg-789",
            "status": "read"
        })
        
        handler.handle_message_status_updated(event)
        
        mock_realtime.emit_new_message.assert_not_called()
    
    def test_message_status_updated_message_not_found(self, handler, mock_repository):
        """message.status.updated: mensagem não encontrada."""
        mock_repository.find_by_id.return_value = None
        
        event = self.create_event("message.status.updated", {
            "message_id": "msg-789",
            "status": "read"
        })
        
        result = handler.handle_message_status_updated(event)
        
        assert result["status"] == "error"
        assert "not found" in result["error"]
    
    # ========== message.reaction.updated ==========
    
    def test_message_reaction_updated_existing_message(self, handler, mock_repository, mock_realtime):
        """message.reaction.updated: atualiza reação de mensagem existente."""
        mock_repository.find_by_id.return_value = {"message_id": "msg-789"}
        
        event = self.create_event("message.reaction.updated", {
            "message_id": "msg-789",
            "reaction": {"emoji": "👍", "action": "added"}
        })
        
        result = handler.handle_message_reaction_updated(event)
        
        assert result["status"] == "updated"
        mock_repository.find_by_id.assert_called_once_with("msg-789")
        mock_repository.update_reaction.assert_called_once()
        mock_realtime.emit_reaction.assert_called_once()
    
    def test_message_reaction_updated_no_creation(self, handler, mock_repository):
        """message.reaction.updated: NÃO cria nova mensagem."""
        mock_repository.find_by_id.return_value = {"message_id": "msg-789"}
        
        event = self.create_event("message.reaction.updated", {
            "message_id": "msg-789",
            "reaction": {"emoji": "👍", "action": "added"}
        })
        
        handler.handle_message_reaction_updated(event)
        
        mock_repository.create.assert_not_called()
    
    def test_message_reaction_updated_no_unread_increment(self, handler, mock_repository):
        """message.reaction.updated: NÃO incrementa unread."""
        mock_repository.find_by_id.return_value = {"message_id": "msg-789"}
        
        event = self.create_event("message.reaction.updated", {
            "message_id": "msg-789",
            "reaction": {"emoji": "👍", "action": "added"}
        })
        
        handler.handle_message_reaction_updated(event)
        
        mock_repository.increment_unread.assert_not_called()
    
    def test_message_reaction_updated_message_not_found(self, handler, mock_repository):
        """message.reaction.updated: mensagem não encontrada."""
        mock_repository.find_by_id.return_value = None
        
        event = self.create_event("message.reaction.updated", {
            "message_id": "msg-789",
            "reaction": {"emoji": "👍", "action": "added"}
        })
        
        result = handler.handle_message_reaction_updated(event)
        
        assert result["status"] == "error"
        assert "not found" in result["error"]
