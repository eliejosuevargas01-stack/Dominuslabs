# EVT-001 — Catálogo de Eventos Atuais

## Dominus Backend (FastAPI)

### Endpoints de Eventos (SSE)

| Endpoint | Método | Descrição | Autenticação |
|----------|--------|-----------|--------------|
| `/events/leads/{lead_id}` | GET | SSE para eventos de um lead específico | JWT + tenant |
| `/events/crm-chats` | GET | SSE para chats CRM | JWT + tenant |
| `/events/{public_token}` | GET | SSE com token público | Token público |
| `/events` | GET | SSE genérico | JWT |

### Endpoints de Webhook (HTTP POST)

| Endpoint | Descrição | Origem |
|----------|-----------|--------|
| `/crm/update-chat` | Atualização de chat CRM | n8n |
| `/crm/message-status` | Status de mensagem | n8n |
| `/github/{public_token}` | Webhook GitHub | GitHub |
| `/github` | Webhook GitHub | GitHub |
| `/deploy` | Webhook deploy | CI/CD |
| `/inbound/whatsapp` | Mensagem WhatsApp recebida | n8n |
| `/inbound/instagram` | Mensagem Instagram recebida | n8n |
| `/waha/session-status` | Status sessão WAHA | WA API |
| `/outbound/whatsapp/send` | Envio WhatsApp | Frontend |

### Eventos Internos (não HTTP)

| Evento | Origem | Destino | Tipo |
|--------|--------|---------|------|
| `reload` | `notify_lead_listeners` | SSE leads | string |
| `CRM_CHAT_RESYNC_EVENT` | `_enqueue_crm_chat_event` | SSE crm-chats | JSON |

---

## WA API (api-whatsapp-service)

### Webhooks Configuráveis por Sessão

| Evento | Descrição | Destino |
|--------|-----------|---------|
| `message` | Mensagem recebida | n8n webhook |
| `session.status` | Status da sessão | n8n webhook |
| `group.join` | Entrada em grupo | n8n webhook |
| `group.leave` | Saída de grupo | n8n webhook |
| `group.update` | Atualização de grupo | n8n webhook |
| `call` | Chamada recebida | n8n webhook |
| `presence.update` | Atualização de presença | n8n webhook |

### Estrutura de Webhook

```javascript
// Configuração por sessão
session.webhook = {
  url: "https://n8n.example.com/webhook/...",
  events: ["message", "session.status", ...]
}
```

---

## n8n Workflows

### Workflows Identificados (do BASELINE.md)

| Workflow | ID | Status | Função |
|----------|-----|--------|--------|
| Dominus AI | YqDBFFzJ1L4FRAvz | Ativo | Processamento IA |
| Dominus AI Buffer | 4ANz4lSb80pCuAT4 | Ativo | Buffer de mensagens |
| dominuslabs_respostas_leads | SpQwyDZsOo3ozXuE | Ativo | Respostas automáticas |
| dominuslabs_crm | WJ37gGiodnAJVkBN | Desativado | CRM |

### Eventos Roteados pelo n8n

| Tipo | Origem | Destino | Descrição |
|------|--------|---------|-----------|
| `message.created` | WA API | Dominus | Nova mensagem |
| `message.updated` | WA API | Dominus | Atualização de mensagem |
| `session.status` | WA API | Dominus | Status da sessão |
| `order.created` | Dominus | n8n | Novo pedido |
| `order.updated` | Dominus | n8n | Atualização de pedido |

---

## IDC (idc-dominuslabs)

### Eventos de Identidade

| Evento | Descrição |
|--------|-----------|
| `token.issued` | Token JWT emitido |
| `token.revoked` | Token revogado |
| `client.registered` | Novo cliente M2M registrado |

---

## Duplicações Semânticas Identificadas

| Problema | Localização | Descrição |
|----------|-------------|-----------|
| `update-chat` vs `message-status` | Dominus webhooks | Dois endpoints para atualizações semânticas similares |
| `reload` genérico | SSE leads/crm-chats | Evento não tipado — recarrega tudo |
| `inbound/whatsapp` vs n8n | Dominus | WA API → n8n → Dominus — múltiplos hops |

---

## Próximos Passos (EVT-002 a EVT-008)

1. **EVT-002**: Criar schema SystemEvent versionado
2. **EVT-003**: Definir tipos canônicos (message.created, message.status.updated, etc.)
3. **EVT-004**: Criar Event Ingress único (`POST /webhooks/events`)
4. **EVT-005**: Implementar Event Router
5. **EVT-006**: Definir regra fundamental de mensagem
6. **EVT-007**: Configurar n8n como router por tipo
7. **EVT-008**: Deprecar endpoints antigos
