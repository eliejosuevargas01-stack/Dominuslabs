# BASELINE — Dominus Product & Architecture Refoundation

> **Status:** HISTORICAL / AUDIT ARTIFACT
> This document records the system at a specific point in time.
> It is NOT the canonical target architecture.
> Canonical sources:
> - `docs/refoundation/GOAL.md`
> - `docs/refoundation/CONTRACTS.md`
> - `docs/architecture.md`

---

> Capturado em: 2026-09-24
> Capturado por: ARCH-000 (Orchestrator)
> Este documento é o ponto de referência para medir progresso. Não alterar após commit.

---

## 1. Commit SHAs

| Repositório | SHA | Branch | Data do commit |
|-------------|-----|--------|----------------|
| `Dominuslabs` | `9d516fd587f8f385831238152aba06ed3066315b` | `main` | 2026-09-23 |
| `api-whatsapp-service` | `c7a05c161a32acc8742b17e5dceef23ec7c5aa92` | `main` | — |
| `idc-dominuslabs` | `3a63aca500a8eb09cc1c155b8b1b6edbbf5dcca9` | `main` | — |

---

## 2. Workflows n8n

| ID | Nome | Status | Função |
|----|------|--------|--------|
| `YqDBFFzJ1L4FRAvz` | Dominus AI | Ativo | Atendimento IA principal |
| `4ANz4lSb80pCuAT4` | Dominus AI Buffer | Ativo | Buffer de mensagens |
| `SpQwyDZsOo3ozXuE` | dominuslabs_respostas_leads | Ativo | Respostas a leads |
| `WJ37gGiodnAJVkBN` | dominuslabs_crm | **Desativado** | CRM (migrado para DB direto) |

n8n URL: `https://myn8n.seommerce.shop`

---

## 3. Variáveis de Ambiente Necessárias (nomes apenas)

### Dominuslabs Backend (`project-hub/backend`)

```
JWT_SECRET
ADMIN_USERNAME
ADMIN_PASSWORD
ADMIN_TENANT_ID
VIEWER_USERNAME
VIEWER_PASSWORD
DATABASE_URL
WEBHOOK_SECRET
N8N_WEBHOOK_SECRET
N8N_TIMESTAMP_TOLERANCE_SECONDS
ENCRYPTION_MASTER_KEY
UPLOAD_DIR
PRODUCT_MEDIA_MAX_BYTES
IDENTITY_WORKER_URL
WHATSAPP_API_URL
WHATSAPP_PUBLIC_URL
DOMINUS_PRIVATE_KEY
DOMINUS_PUBLIC_KEY
IDPW_PUBLIC_KEY
WHATS_API_PUBLIC_KEY
N8N_PUBLIC_KEY
LITELLM_API_KEY
LITELLM_API_BASE
CRM_GET_LEADS_WEBHOOK_URL
CRM_CREATE_LEAD_WEBHOOK_URL
CRM_UPDATE_LEAD_WEBHOOK_URL
CRM_DELETE_LEAD_WEBHOOK_URL
CRM_GET_MESSAGES_WEBHOOK_URL
CRM_CREATE_MESSAGE_WEBHOOK_URL
CRM_SEND_WHATSAPP_WEBHOOK_URL
CRM_UPDATE_STATUS_WEBHOOK_URL
CRM_CREATE_ACTIVITY_WEBHOOK_URL
ACCEPT_ORDER_WEBHOOK_URL
```

### Whats API (`api-whatsapp-service`)

```
NODE_ENV
HOST
PORT
LOG_LEVEL
PG_CONNECTION_STRING
TRUST_PROXY
JWT_ISSUER
JWT_SUBJECT
JWT_AUDIENCE
IDPW_JWT_KID
IDPW_JWKS_URL
WHATS_API_PRIVATE_KEY
DOMINUS_PUBLIC_KEY
N8N_WEBHOOK_URL
N8N_WEBHOOK_SECRET
N8N_WEBHOOK_TIMEOUT_MS
N8N_WEBHOOK_ENABLED
N8N_WEBHOOK_PRIVATE
N8N_WEBHOOK_GROUPS
N8N_WEBHOOK_NEWSLETTERS
N8N_WEBHOOK_BROADCASTS
N8N_WEBHOOK_FROM_ME
AUTO_CONNECT
SYNC_FULL_HISTORY
TYPING_DELAY_ENABLED
DISABLE_MESSAGE_STORE
MAX_STORED_MESSAGES
RATE_LIMIT_MAX
RATE_LIMIT_WINDOW
BODY_LIMIT_MB
SESSIONS_DIR
DATA_DIR
MEDIA_DIR
REQUIRE_SECURE_MEDIA
ANTIBAN_OPTOUT_KEYWORDS
```

### IDC (`idc-dominuslabs`)

```
JWT_ISSUER
JWT_KID
JWT_EXPIRATION_SECONDS
JWT_WORKER_PRIVATE_KEY
WORKER_PRIVATE_KEY
DOMINUS_PUBLIC_KEY
REQUEST_MAX_SKEW_SECONDS
POLICY_VERSION
ALLOWED_CLIENTS
ALLOWED_AUDIENCES
ALLOWED_SCOPES
```

---

## 4. Endpoints em Uso

### Dominuslabs Backend (`:8000/api/v1`)

| Método | Path | Descrição |
|--------|------|-----------|
| POST | `/auth/login` | Login humano |
| GET | `/auth/me` | Perfil do usuário autenticado |
| GET | `/crm/dashboard` | Métricas CRM (contacts) |
| GET | `/crm/leads` | Lista leads/contacts |
| GET | `/crm/conversations` | Lista conversas WhatsApp |
| GET | `/crm/chat-history` | Histórico de mensagens |
| POST | `/crm/send-message` | Enviar mensagem WhatsApp |
| POST | `/webhooks/inbound/whatsapp` | Inbound de eventos WhatsApp |
| POST | `/webhooks/n8n/crm-update` | Callback n8n CRM |
| GET | `/orders` | Lista pedidos |
| POST | `/orders` | Criar pedido |
| PATCH | `/orders/{id}/status` | Atualizar status do pedido |
| GET | `/products` | Lista produtos/cardápio |
| GET | `/company/settings` | Configurações da empresa |
| GET | `/analytics/orders` | Métricas de pedidos |

### Whats API (`:3000`)

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/sessions` | Lista sessões WhatsApp |
| POST | `/sessions` | Criar sessão |
| DELETE | `/sessions/{id}` | Remover sessão |
| GET | `/sessions/{id}/qr` | QR code |
| POST | `/messages/send` | Enviar mensagem |
| GET | `/media/{id}` | Download de mídia |
| GET | `/conversations` | Lista conversas |
| GET | `/messages/{sessionId}/{jid}` | Histórico de mensagens |
| POST | `/webhook` | Webhook para n8n |

### IDC (`idc-dominuslabs`)

| Método | Path | Descrição |
|--------|------|-----------|
| POST | `/token` | Emitir JWT M2M (300s TTL) |
| GET | `/.well-known/jwks.json` | JWKS público |

---

## 5. Eventos Emitidos e Consumidos

### WA API → n8n (via webhook)

```
message.received    — nova mensagem inbound
message.sent        — mensagem outbound confirmada
message.status      — delivered/read/played
session.connected   — sessão WhatsApp conectada
session.disconnected— sessão WhatsApp desconectada
session.qr          — QR code atualizado
```

### n8n → Dominus (via webhook)

```
crm.update_chat     — atualizar conversa no CRM
crm.new_message     — nova mensagem para exibir
crm.message_status  — atualização de status de mensagem
order.created       — novo pedido criado pela IA
```

### Dominus → Frontend (via SSE)

```
GET /api/v1/sse/crm-chats   — stream de eventos CRM
```

---

## 6. Suites de Teste — Resultado em 2026-09-24

### Dominuslabs Backend (`project-hub/backend`)

```
Comando: python -m pytest --tb=no -q
Resultado: 3 failed, 204 passed, 14 warnings
Falhas conhecidas:
  - tests/test_crm.py::test_get_leads — assert 0 == 1
  - tests/test_crm.py::test_tenant_isolation_leads_by_db — assert 0 == 1
  - tests/test_crm.py::test_get_leads_with_multiple_tenants — assert 0 == 2
  (Relacionado à migração de leads → contacts no commit 9d516fd5)
```

### Dominuslabs Frontend (`src/`)

```
Comando: npx vitest run
Resultado: 10 test files passed, 58 tests passed
```

### Whats API (`api-whatsapp-service`)

```
Comando: npx vitest run
Resultado: 13 test files passed, 222 tests passed
```

### IDC (`idc-dominuslabs`)

```
Comando: npx vitest run
Resultado: 1 test file passed, 9 tests passed
```

---

## 7. Problemas Conhecidos (16 itens)

| # | Problema | Severidade | Localização |
|---|----------|-----------|-------------|
| 1 | "Pedidos Hoje" exibe histórico quando hoje está vazio | 🔴 | `DashboardOperationalView.tsx:132` |
| 2 | Métricas de IA usam valores hardcoded (14, 2, 88) | 🔴 | `DashboardOperationalView.tsx:178-180` |
| 3 | Sessão inicial pode ser desconectada (fallback silencioso) | 🔴 | `OmnichannelView.tsx` |
| 4 | Imagens sem experiência adequada de expansão | 🟡 | `OmnichannelView.tsx` |
| 5 | Vídeos sem viewer/fullscreen adequado | 🟡 | `OmnichannelView.tsx` |
| 6 | Stickers caem no renderer genérico de imagem | 🟡 | `OmnichannelView.tsx` |
| 7 | Avatares da sidebar não seguem o mesmo pipeline do chat | 🟡 | `OmnichannelView.tsx` |
| 8 | Notificações WhatsApp só funcionam com Omnichannel montado | 🔴 | `OmnichannelView.tsx` |
| 9 | Status update pode resultar em som de nova mensagem | 🟡 | `OmnichannelView.tsx` |
| 10 | Browser notifications não existem | 🟡 | — |
| 11 | Mobile usa sidebar/drawer desktop adaptado | 🟡 | Layout principal |
| 12 | Drawer tem problema de sobreposição próximo ao logo | 🟡 | Layout principal |
| 13 | Omnichannel mobile perde área útil com múltiplos headers | 🟡 | `OmnichannelView.tsx` |
| 14 | Company Settings possui overflow horizontal ruim | 🟡 | `CompanySettingsView.tsx` |
| 15 | Project Hub aparece para tenants | 🟡 | Menu/sidebar |
| 16 | Não existe Meu Perfil | 🟡 | — |

---

## 8. Estado Visual Atual (descrição textual)

### Desktop
- Sidebar esquerda com menu: Início, Atendimento, Pedidos, Clientes, Campanhas, Automações, Cardápio, Canais, Integrações, IA, Minha Empresa, Project Hub, Cases & Portfólio
- Dashboard com métricas: Pedidos Hoje, Faturamento Hoje, Ticket Médio, % IA
- Omnichannel: sidebar de conversas + painel de chat lado a lado

### Mobile
- Drawer lateral (hamburger) como navegação principal — mesmo menu do desktop
- Omnichannel: tenta reproduzir layout desktop comprimido
- Overflow horizontal em Company Settings

---

## 9. Arquivos Monolíticos Identificados

| Arquivo | Linhas | Prioridade de decomposição |
|---------|--------|---------------------------|
| `src/pages/OmnichannelView.tsx` | 2725 | 🔴 Crítica (Fase 7) |
| `src/pages/OrderManagerView.tsx` | 1353 | 🟡 (Fase 10) |
| `src/pages/CompanySettingsView.tsx` | 1297 | 🟡 (Fase 10) |
| `project-hub/backend/app/webhooks.py` | ~1178 | 🟡 (Fase 12) |
| `project-hub/backend/app/services/n8n_service.py` | ~1524 | 🟡 (Fase 12) |
| `api-whatsapp-service/src/services/session.manager.js` | ~2347 | 🟡 (Fase 12) |

---

## 10. Dependências Externas

| Serviço | URL | Uso |
|---------|-----|-----|
| IDPW | `https://idc-dominuslabs.eliejosuevargas01.workers.dev` | Autenticação M2M |
| n8n | `https://myn8n.seommerce.shop` | Automações e workflows |
| Produção | `https://dominuslabs.online` | Dominus em produção |
| VPS | `72.60.247.157:2222` | Coolify, Docker |
