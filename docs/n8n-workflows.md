# n8n Workflows — Dominus

> **Status:** CURRENT_RUNTIME_ONLY — Este documento descreve o comportamento atual.
> Para a arquitetura planejada, consulte `docs/refoundation/GOAL.md` e `docs/architecture.md`.

---

## Visão Geral

O n8n atua como **orquestrador de eventos** no meio do fluxo de mensagens do Dominus.

### CURRENT RUNTIME

```
Whats API
  → POST /webhook/lead_responses
  → n8n valida HMAC
  → n8n upsert PostgreSQL
  → n8n chama /api/v1/webhooks/crm/update-chat
  → Backend emite SSE
```

### TARGET ARCHITECTURE

```
Whats API
  → POST /webhook/events (Event Ingress)
  → Dominus EventIngress
  → EventValidator
  → EventRouter
  → Handler específico
```

---

## CURRENT RUNTIME — Detalhes

### Fluxo de Mensagem Recebida

```
WhatsApp (mensagem do cliente)
    ↓
Baileys / Whats API
    ↓
POST /webhook/lead_responses (n8n)
    ↓
n8n valida HMAC
    ↓
n8n upsert PostgreSQL (contacts, messages, conversations)
    ↓
n8n notifica backend via /api/v1/webhooks/crm/update-chat
    ↓
Backend emite SSE
    ↓
Frontend recebe atualização em tempo real
```

### Segurança

- HMAC-SHA256 entre Whats API ↔ n8n
- HMAC-SHA256 entre n8n ↔ Backend
- Headers: `X-Webhook-Signature`, `X-Webhook-Timestamp`, `X-Webhook-Event-ID`

---

## TARGET ARCHITECTURE — Mudanças Planejadas

### 1. Event Contract Unificado

Atualmente, eventos usam nomes variados e endpoints múltiplos. O target introduz um contrato único:

```json
{
  "version": 1,
  "event_id": "uuid",
  "type": "message.created",
  "tenant_id": "tenant",
  "session_id": "session",
  "occurred_at": "ISO-8601",
  "payload": {}
}
```

### 2. Event Ingress no Dominus

Novo endpoint: `POST /webhooks/events`

Responsabilidades:
- Signature validation
- Timestamp validation
- Event ID deduplication
- Idempotency
- Tenant validation
- Schema validation
- Routing

### 3. n8n como Router, não Tradutor Semântico

**CURRENT:** n8n modifica o tipo do evento durante o pipeline

**TARGET:** n8n roteia por `type` sem alterar a semântica

```
type
├── message.created
├── message.status.updated
├── media.ready
├── session.connected
└── ...
```

### 4. Regra Fundamental de Mensagem

`message.status.updated`:
- ✅ Pode: atualizar status, checks, timestamp
- ❌ NÃO pode: incrementar unread, criar nova mensagem, tocar som, emitir browser notification

---

## Migração

### Fases

1. **EVT-001**: Catalogar eventos atuais ✅
2. **EVT-002**: Criar schema SystemEvent (pendente)
3. **EVT-003**: Definir tipos canônicos (pendente)
4. **EVT-004**: Implementar Event Ingress (pendente)
5. **EVT-005**: Criar Event Router (pendente)
6. **EVT-006**: Migrar n8n para usar novos tipos (pendente)
7. **EVT-007**: Deprecar endpoints antigos (pendente)

### Verificação

Antes de remover endpoints antigos:
1. Descobrir todos os consumidores
2. Migrá-los para o novo contrato
3. Criar logs temporários para detectar chamadas restantes
4. Remover endpoints sem consumidor

---

## Workflows Ativos

> **Nota:** IDs e URLs específicos foram removidos por segurança.

| Nome | Status | Função |
|------|--------|--------|
| Respostas Leads | Ativo | Recebe webhook, valida HMAC, salva mensagem, notifica backend |
| Dominus AI | Ativo | Agente conversacional, processa mensagens recebidas |
| Dominus AI Buffer | Ativo | Buffer/fila para gerenciar concorrência |

---

## Banco de Dados

O n8n escreve nas seguintes tabelas:

### messages

| Campo | Descrição |
|-------|-----------|
| `message_id` | ID único |
| `contact_jid` | Identificador JID |
| `session_id` | ID da sessão WhatsApp |
| `content` | Texto |
| `is_from_me` | Se foi enviada pelo sistema |
| `media_url` | URL do arquivo (TARGET: state machine) |
| `status` | Status da mensagem |
| `tenant_id` | ID do tenant |

### conversations

| Campo | Descrição |
|-------|-----------|
| `contact_jid` | Identificador JID |
| `session_id` | ID da sessão |
| `last_message_preview` | Prévia do texto |
| `last_message_timestamp` | Timestamp |
| `unread_count` | Contador |
| `tenant_id` | ID do tenant |

### contacts

| Campo | Descrição |
|-------|-----------|
| `contact_jid` | Identificador JID |
| `push_name` | Nome de exibição |
| `display_phone` | Número formatado |
| `profile_pic_url` | URL da foto |
| `tenant_id` | ID do tenant |

---

## Configuração

### Credenciais Necessárias

| Tipo | Uso |
|------|-----|
| PostgreSQL | Conexão com banco Dominus |
| HMAC Secret | Validação de websockets |

### Variáveis

- `WEBHOOK_SECRET` — Chave HMAC para validação
- URLs dos endpoints backend

---

## Referências

- `docs/architecture.md` — Arquitetura geral
- `docs/refoundation/GOAL.md` — Princípios do Refoundation
- `docs/refoundation/EVT_CATALOG.md` — Catálogo de eventos (HISTORICAL)
