"""
Documentação do módulo crm_service.py.

O que faz: Implementa acesso direto ao banco PostgreSQL para operações CRM, eliminando a dependência do n8n.
Impacto na regra de negócio: Garante que operações CRM funcionem mesmo sem o workflow do n8n.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
from datetime import datetime, timezone
import logging

logger = logging.getLogger("crm_service")


async def get_contacts(db: Session, tenant_id: str) -> List[dict]:
    """
    Recupera todos os contatos de um tenant direto do banco.
    Enforces Zero-Trust by filtering strictly by tenant_id.
    
    Args:
        db: Database session
        tenant_id: Tenant identifier for isolation
        
    Returns:
        List of contacts with tenant_id enforced
    """
    if not tenant_id:
        logger.error("[Zero-Trust] get_contacts chamado sem tenant_id!")
        raise ValueError("[Zero-Trust] tenant_id é obrigatório para get_contacts")
    
    q = """
        SELECT
            contact_jid,
            push_name,
            display_phone,
            profile_pic_url,
            created_at,
            updated_at,
            tenant_id
        FROM contacts
        WHERE tenant_id = :tenant_id
        ORDER BY created_at DESC
    """
    rows = db.execute(sa_text(q), {"tenant_id": tenant_id}).fetchall()
    result = []
    for row in rows:
        d = dict(row._mapping)
        result.append(d)
    return result


async def get_conversations(db: Session, tenant_id: str) -> List[dict]:
    """
    Recupera todas as conversas de um tenant direto do banco.
    Enforces Zero-Trust by filtering strictly by tenant_id.
    JOIN com contacts para obter informações adicionais (push_name, display_phone, profile_pic_url).
    
    Args:
        db: Database session
        tenant_id: Tenant identifier for isolation
        
    Returns:
        List of conversations with tenant_id enforced
    """
    if not tenant_id:
        logger.error("[Zero-Trust] get_conversations chamado sem tenant_id!")
        raise ValueError("[Zero-Trust] tenant_id é obrigatório para get_conversations")
    
    q = """
        SELECT
            conv.contact_jid,
            conv.session_id,
            conv.unread_count,
            conv.last_message_preview,
            conv.last_message_timestamp,
            conv.participant_pushname,
            conv.participant,
            conv.tenant_id,
            conv.updated_at,
            conv.created_at,
            c.push_name AS contact_push_name,
            c.display_phone AS contact_display_phone,
            c.profile_pic_url AS contact_profile_pic_url
        FROM conversations conv
        LEFT JOIN contacts c ON c.contact_jid = conv.contact_jid AND c.tenant_id = conv.tenant_id
        WHERE conv.tenant_id = :tenant_id
        ORDER BY conv.last_message_timestamp DESC NULLS LAST
    """
    params = {"tenant_id": tenant_id}
    rows = db.execute(sa_text(q), params).fetchall()
    
    result = []
    for row in rows:
        ts = row.last_message_timestamp
        ts_iso = ts.isoformat() if ts else ""
        ca = row.created_at
        ca_iso = ca.isoformat() if ca else ""
        
        result.append({
            "contact_jid": row.contact_jid,
            "session_id": row.session_id,
            "push_name": row.contact_push_name or row.participant_pushname or row.contact_jid,
            "display_phone": row.contact_display_phone,
            "profile_pic_url": row.contact_profile_pic_url or "",
            "unread_count": row.unread_count or 0,
            "last_message_preview": row.last_message_preview or "",
            "last_message_timestamp": ts_iso,
            "participant_pushname": row.participant_pushname,
            "participant": row.participant,
            "tenant_id": row.tenant_id,
            "created_at": ca_iso,
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        })
    return result


async def get_messages(db: Session, contact_jid: str, session_id: str, tenant_id: str) -> List[dict]:
    """
    Recupera mensagens de um contato direto do banco.
    Enforces Zero-Trust by filtering strictly by tenant_id.
    
    Args:
        db: Database session
        contact_jid: Contact identifier
        session_id: Session identifier
        tenant_id: Tenant identifier for isolation
        
    Returns:
        List of messages with tenant_id enforced
    """
    if not tenant_id:
        logger.error("[Zero-Trust] get_messages chamado sem tenant_id!")
        raise ValueError("[Zero-Trust] tenant_id é obrigatório para get_messages")
    
    q = """
        SELECT
            message_id,
            contact_jid,
            session_id,
            is_from_me,
            chat_kind,
            message_type,
            status,
            content,
            message_timestamp,
            created_at,
            media_url,
            participant,
            participant_pushname,
            quoted_message_id,
            quoted_participant,
            quoted_text,
            reaction_text,
            reaction_target_message_id,
            reaction_target_sender_jid,
            tenant_id
        FROM messages
        WHERE tenant_id = :tenant_id
          AND contact_jid = :contact_jid
          AND session_id = :session_id
        ORDER BY message_timestamp ASC
    """
    params = {
        "tenant_id": tenant_id,
        "contact_jid": contact_jid,
        "session_id": session_id
    }
    rows = db.execute(sa_text(q), params).fetchall()
    
    result = []
    for m in rows:
        ts = m.message_timestamp
        ts_iso = ts.isoformat() if ts else ""
        ca = m.created_at
        ca_iso = ca.isoformat() if ca else ""
        is_from_me = bool(m.is_from_me) if m.is_from_me is not None else False
        
        result.append({
            "message_id": m.message_id,
            "id": m.message_id,
            "contact_jid": m.contact_jid,
            "session_id": m.session_id,
            "is_from_me": is_from_me,
            "sender": "user" if is_from_me else "lead",
            "direction": "outgoing" if is_from_me else "incoming",
            "chat_kind": m.chat_kind or "private",
            "message_type": m.message_type or "conversation",
            "content": m.content or "",
            "message": m.content or "",
            "status": m.status or "received",
            "message_timestamp": ts_iso,
            "timestamp": ts_iso,
            "created_at": ca_iso,
            "media_url": m.media_url,
            "participant": m.participant,
            "participant_pushname": m.participant_pushname,
            "quoted_message_id": m.quoted_message_id,
            "quoted_participant": m.quoted_participant,
            "quoted_text": m.quoted_text,
            "reaction_text": m.reaction_text,
            "reaction_target_message_id": m.reaction_target_message_id,
            "reaction_target_sender_jid": m.reaction_target_sender_jid,
            "tenant_id": m.tenant_id,
        })
    return result


# Legacy alias for compatibility with n8n_service.py
class CRMService:
    """
    CRMService class for direct database access without n8n webhook dependency.
    Provides Zero-Trust tenant isolation for all operations.
    """
    
    @staticmethod
    async def get_contacts(tenant_id: str) -> List[dict]:
        """Alias for get_contacts to maintain compatibility."""
        from app.core.database import get_db
        db = next(get_db())
        try:
            return await get_contacts(db, tenant_id)
        finally:
            db.close()
    
    @staticmethod
    async def get_conversations(tenant_id: str) -> List[dict]:
        """Alias for get_conversations to maintain compatibility."""
        from app.core.database import get_db
        db = next(get_db())
        try:
            return await get_conversations(db, tenant_id)
        finally:
            db.close()
    
    @staticmethod
    async def get_messages(contact_jid: str, session_id: str, tenant_id: str) -> List[dict]:
        """Alias for get_messages to maintain compatibility."""
        from app.core.database import get_db
        db = next(get_db())
        try:
            return await get_messages(db, contact_jid, session_id, tenant_id)
        finally:
            db.close()
