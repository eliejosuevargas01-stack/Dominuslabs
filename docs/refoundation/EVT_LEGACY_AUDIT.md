# EVT-003 — Auditoria de Strings Antigas

## LEGACY TERM | FILE | CURRENT MEANING | CANONICAL TARGET | MIGRATION TASK

### Backend (FastAPI)

| Termo | Arquivo | Significado Atual | Tipo Canônico | Task de Migração |
|-------|---------|-------------------|---------------|------------------|
| `new_message` | `app/api/endpoints/webhooks.py:453` | Ação de nova mensagem | `message.created` | EVT-004/005 |
| `new_message` | `app/api/endpoints/webhooks.py:454` | Evento de nova mensagem | `message.created` | EVT-004/005 |
| `update-chat` | `app/api/endpoints/webhooks.py:483` | Endpoint de atualização de chat | `conversation.updated` | EVT-004/005 |
| `message.updated` | `app/api/endpoints/webhooks.py:548` | Status da mensagem | `message.status.updated` | EVT-004/005 |
| `message-status` | `app/api/endpoints/webhooks.py:559` | Endpoint de status de mensagem | `message.status.updated` | EVT-004/005 |

### Frontend (React)

| Termo | Arquivo | Significado Atual | Tipo Canônico | Task de Migração |
|-------|---------|-------------------|---------------|------------------|
| `message.updated` | `src/pages/OmnichannelView.tsx:1318` | Atualização de mensagem | `message.status.updated` | EVT-007 |
| `new_message` | `src/pages/OmnichannelView.tsx:1328` | Nova mensagem | `message.created` | EVT-007 |

---

## Resumo

- **Total de termos legacy encontrados:** 7
- **Backend:** 5 ocorrências
- **Frontend:** 2 ocorrências

**Não substituir nesta task.** A migração pertence a EVT-004/005/006/007/008.
