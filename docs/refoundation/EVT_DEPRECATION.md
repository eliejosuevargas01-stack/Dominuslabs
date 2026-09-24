# EVT-008 — Deprecação de Endpoints Antigos

## Endpoints Deprecados

Os seguintes endpoints foram marcados como `deprecated=True` e serão removidos em versão futura:

| Endpoint | Método | Substituto | Status |
|----------|--------|-----------|--------|
| `/crm/update-chat` | POST | `POST /api/v1/webhooks/events` (type=`conversation.updated`) | ✅ Deprecado |
| `/crm/update-chat` | GET | `GET /api/v1/events/crm-chats` (SSE) | ✅ Deprecado |
| `/crm/message-status` | POST | `POST /api/v1/webhooks/events` (type=`message.status.updated`) | ✅ Deprecado |
| `/inbound/whatsapp` | POST | `POST /api/v1/webhooks/events` (type=`message.created`) | ✅ Deprecado |
| `/inbound/instagram` | POST | `POST /api/v1/webhooks/events` (type=`message.created`) | ✅ Deprecado |
| `/waha/session-status` | POST | `POST /api/v1/webhooks/events` (type=`session.connected`/`session.disconnected`) | ✅ Deprecado |

## Migração

### Antes (Legacy)

```bash
curl -X POST https://dominuslabs.online/api/v1/crm/update-chat \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "123",
    "chat_id": "456",
    "messages": [...]
  }'
```

### Depois (SystemEvent)

```bash
curl -X POST https://dominuslabs.online/api/v1/webhooks/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "version": 1,
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "conversation.updated",
    "tenant_id": "tenant-123",
    "session_id": "session-456",
    "occurred_at": "2026-09-24T02:00:00Z",
    "payload": {
      "contact_id": "123",
      "chat_id": "456",
      "messages": [...]
    }
  }'
```

## Timeline

- **2026-09-24**: Endpoints marcados como deprecated
- **2026-10-24**: Aviso de remoção (30 dias)
- **2026-11-24**: Remoção dos endpoints (60 dias)

## Notas

- Endpoints deprecados continuam funcionando durante o período de transição
- Logs de uso serão monitorados para identificar consumers ativos
- Migração deve ser feita antes da data de remoção
