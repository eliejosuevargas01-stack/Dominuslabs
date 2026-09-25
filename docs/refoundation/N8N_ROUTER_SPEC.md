# EVT-007 — n8n como Router

> **Status:** MIGRATION SPEC — NON-CANONICAL
> Este documento detalha a migração EVT-007. Ele não substitui os contratos canônicos.
> Authority: `docs/refoundation/GOAL.md`, `CONTRACTS.md` e `docs/architecture.md`.

---

## Visão Geral

O n8n atua como **roteador inteligente** entre o WA API (WhatsApp) e o Dominus backend.
Ele recebe webhooks do WA API, transforma em eventos canônicos, e envia para o Event Ingress do Dominus.

## Fluxo Atual vs. Novo Fluxo

### Fluxo Atual (Legacy)

```
WA API → n8n → Dominus (múltiplos endpoints)
         ↓
    /crm/update-chat
    /crm/message-status
    /inbound/whatsapp
    /waha/session-status
```

**Problemas:**
- Múltiplos endpoints com semânticas sobrepostas
- Eventos não tipados
- Difícil rastreabilidade
- Duplicação de lógica

### Novo Fluxo (Refoundation)

```
WA API → n8n → Dominus Event Ingress
         ↓
    POST /api/v1/webhooks/events
    {
      "version": 1,
      "event_id": "uuid",
      "type": "message.created",
      "tenant_id": "tenant-123",
      "session_id": "session-456",
      "occurred_at": "2026-09-24T02:00:00Z",
      "payload": { ... }
    }
```

**Vantagens:**
- Endpoint único
- Eventos tipados e validados
- Rastreabilidade completa
- Fácil evolução

## Mapeamento de Eventos

### WA API → SystemEvent

| Evento WA API | Tipo Canônico | Transformação |
|---------------|---------------|---------------|
| `message` | `message.created` | Extrair payload, gerar UUID, adicionar tenant/session |
| `session.status` | `session.connected` / `session.disconnected` | Mapear status para tipo apropriado |
| `group.join` | `conversation.updated` | Atualização de conversa |
| `group.leave` | `conversation.updated` | Atualização de conversa |
| `call` | `conversation.updated` | Atualização de conversa (chamada) |
| `presence.update` | `conversation.updated` | Atualização de presença |

### n8n Workflows

#### Dominus AI (YqDBFFzJ1L4FRAvz)

**Função:** Processamento de mensagens com IA

**Mudanças necessárias:**
1. Receber webhook do WA API
2. Transformar em SystemEvent
3. Enviar para `POST /api/v1/webhooks/events`
4. Remover chamadas diretas para endpoints legados

#### Dominus AI Buffer (4ANz4lSb80pCuAT4)

**Função:** Buffer de mensagens

**Mudanças necessárias:**
1. Bufferizar eventos SystemEvent (não mensagens raw)
2. Enviar em lote para Event Ingress
3. Manter ordenação por `occurred_at`

#### dominuslabs_respostas_leads (SpQwyDZsOo3ozXuE)

**Função:** Respostas automáticas a leads

**Mudanças necessárias:**
1. Receber eventos `message.created` do Event Ingress
2. Processar resposta
3. Enviar resposta via WA API (não via webhook direto)

#### dominuslabs_crm (WJ37gGiodnAJVkBN) — DESATIVADO

**Função:** CRM

**Mudanças necessárias:**
- Reativar apenas após migração para SystemEvent
- Substituir chamadas para `/crm/update-chat` por eventos `conversation.updated`

## Configuração n8n

### Webhook Node (WA API → n8n)

```json
{
  "parameters": {
    "path": "whatsapp-webhook",
    "responseMode": "responseNode",
    "options": {}
  },
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 1,
  "position": [0, 0]
}
```

### Transform Node (n8n → SystemEvent)

```javascript
// Transformar payload WA API em SystemEvent
const event = {
  version: 1,
  event_id: $uuid(),
  type: mapEventType($input.item.json.event),
  tenant_id: $input.item.json.tenant_id,
  session_id: $input.item.json.session_id,
  occurred_at: new Date().toISOString(),
  payload: $input.item.json.data
};

function mapEventType(waEvent) {
  const mapping = {
    'message': 'message.created',
    'session.status': 'session.connected', // ou disconnected
    'group.join': 'conversation.updated',
    'group.leave': 'conversation.updated',
    'call': 'conversation.updated',
    'presence.update': 'conversation.updated'
  };
  return mapping[waEvent] || 'conversation.updated';
}

return { json: event };
```

### HTTP Request Node (n8n → Dominus)

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://dominuslabs.online/api/v1/webhooks/events",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Authorization",
          "value": "Bearer {{$credentials.token}}"
        },
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ]
    },
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {
          "name": "version",
          "value": "={{$json.version}}"
        },
        {
          "name": "event_id",
          "value": "={{$json.event_id}}"
        },
        {
          "name": "type",
          "value": "={{$json.type}}"
        },
        {
          "name": "tenant_id",
          "value": "={{$json.tenant_id}}"
        },
        {
          "name": "session_id",
          "value": "={{$json.session_id}}"
        },
        {
          "name": "occurred_at",
          "value": "={{$json.occurred_at}}"
        },
        {
          "name": "payload",
          "value": "={{$json.payload}}"
        }
      ]
    },
    "options": {}
  },
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 3,
  "position": [400, 0]
}
```

## Checklist de Migração

- [ ] Atualizar workflow Dominus AI para usar SystemEvent
- [ ] Atualizar workflow Dominus AI Buffer para usar SystemEvent
- [ ] Atualizar workflow dominuslabs_respostas_leads para usar SystemEvent
- [ ] Reativar workflow dominuslabs_crm com SystemEvent
- [ ] Testar fluxo completo WA API → n8n → Dominus
- [ ] Validar idempotência (event_id único)
- [ ] Validar ordenação (occurred_at)
- [ ] Validar tenant isolation

## Notas

- O n8n continua sendo o tradutor semântico entre WA API e Dominus
- Event Ingress valida e roteia eventos internamente
- Endpoints legados serão deprecados em EVT-008
