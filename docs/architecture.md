# Arquitetura do Dominus

> **Status:** CANONICAL — Target Architecture

Este documento descreve a arquitetura do sistema Dominus, conforme definido no Refoundation.

---

## Visão Geral

Dominus é uma plataforma SaaS multi-tenant que funciona como funcionário digital e sistema operacional para pequenos e médios negócios.

---

## Diagrama de Arquitetura

```
                    ┌─────────────────────────────────────┐
                    │            TRUST BOUNDARY            │
                    │                                     │
┌──────────┐       │   ┌────────────────────────┐       │
│  Browser │──────────▶│      Frontend (React)  │       │
└──────────┘       │   └───────────┬────────────┘       │
                   │               │                     │
                   │               ▼                     │
                   │   ┌────────────────────────┐       │
                   │   │    Backend (FastAPI)   │       │
                   │   │                        │       │
                   │   │  ┌──────────────────┐  │       │
                   │   │  │ Auth (Human)     │  │       │
                   │   │  │ Tenant Resolver  │  │       │
                   │   │  │ Permissions      │  │       │
                   │   │  │ Session Ownership │  │       │
                   │   │  │ WhatsAppClient   │  │       │
                   │   │  └──────────────────┘  │       │
                   │   └───────────┬────────────┘       │
                   │               │                     │
                   └───────────────┼─────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌───────────┐  ┌───────────┐  ┌───────────┐
            │   IDPW    │  │ Whats API │  │  Postgres │
            │  (M2M)    │  │ (Resource)│  │   (DB)    │
            └─────┬─────┘  └─────┬─────┘  └───────────┘
                  │              │
                  │              │
                  │        ┌─────▼─────┐
                  │        │  WhatsApp │
                  │        │  (Baileys)│
                  │        └───────────┘
                  │              │
                  │        ┌─────▼─────┐
                  │        │    n8n    │
                  │        │(Automation│
                  │        └───────────┘
                  │              │
                  └──────────────┘
```

---

## Trust Boundaries

### Dominus — Business Control Plane

**É o:**
- Backend do produto
- Único intermediário do frontend
- Business control plane

**Responsável por:**
- Autenticação humana
- Resolução de tenant
- Autorização e permissões
- Regras de negócio
- Ownership de sessão
- Integração com IDPW
- Integração com Whats API
- Pedidos, clientes, CRM, empresa, analytics
- Event ingress
- Realtime para frontend

### IDPW — M2M Identity Provider

**É exclusivamente:**
- M2M Identity Provider
- JWT issuance authority

**Responsável por:**
- Validar identidade do Dominus
- Validar request M2M
- Aplicar policy
- Prevenir replay
- Emitir JWT curto RS256
- Publicar JWKS

**NÃO possui:**
- Usuário humano
- CRM
- Sessão WhatsApp
- Regra de negócio
- Mensagens
- Pedidos

### Whats API — Resource Server

**É:**
- WhatsApp Resource Server

**Responsável por:**
- Baileys (WebSocket WhatsApp)
- Sessões
- Mensagens
- Contatos
- Avatares
- Mídia
- Estado WhatsApp
- Persistência relacionada ao WhatsApp
- Dispatch de eventos

**NÃO:**
- Emite autoridade M2M
- Autentica usuário humano
- Decide tenant vindo do browser
- Possui admin/master JWT

### n8n — Event Router

**É:**
- Trust/event boundary real

**Responsável por:**
- Automações
- Agente conversacional
- Workflows
- Integração de eventos
- Encaminhamento de pedidos

---

## Fluxo de Autenticação

### Usuário Humano

```
Browser
  → POST /api/v1/auth/login
  → Dominus valida credenciais
  → Dominus emite JWT de sessão
  → Browser armazena JWT
  → Requisições subsequentes com Bearer token
```

### M2M (Dominus → Whats API)

```
Dominus
  → Solicita JWT M2M ao IDPW
  → IDPW valida assinatura Dominus
  → IDPW emite JWT RS256 curto (≤300s)
  → Dominus usa JWT para chamar Whats API
  → Whats API valida JWT via JWKS
```

**O browser NUNCA recebe:**
- JWT M2M
- Private keys
- Credenciais internas
- Tenant ID como autoridade

---

## Event Contract

### Contrato Base

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

### Tipos Canônicos

| Tipo | Descrição |
|------|-----------|
| `message.created` | Nova mensagem |
| `message.status.updated` | Status lido/entregue |
| `message.reaction.updated` | Reação |
| `conversation.updated` | Atualização de conversa |
| `media.processing` | Mídia sendo processada |
| `media.ready` | Mídia disponível |
| `media.failed` | Falha no processamento |
| `session.connected` | Sessão conectada |
| `session.disconnected` | Sessão desconectada |
| `session.qr.updated` | QR code atualizado |
| `order.created` | Pedido criado |
| `order.updated` | Pedido atualizado |
| `order.cancelled` | Pedido cancelado |

### Regras de Eventos

- Um evento **NUNCA** muda de semântica durante o pipeline
- `message.status.updated` **NUNCA** é tratado como `message.created`
- `message.status.updated` **NUNCA** dispara som ou notification

---

## Media Ownership

### Responsabilidade

**Whats API é proprietária do lifecycle da mídia.**

### Fluxo

```
WhatsApp
  → Mensagem com mídia
  → downloadMediaMessage()
  → Persistência local
  → URL interna controlada
  → GET /api/sessions/{session}/media
  → Dominus → Frontend
```

### Estados

```
pending → downloading → ready | failed
```

### O Frontend NÃO Depende De

- `pps.whatsapp.net`
- `fbcdn.net`
- `directPath`
- URLs temporárias do WhatsApp

---

## Realtime Architecture

### RealtimeProvider Global

O realtime **NÃO** pertence ao OmnichannelView.

```
Authenticated App
└── RealtimeProvider
    ├── WhatsApp events
    ├── Orders events
    ├── Deduplication
    ├── Notification Engine
    └── Sound Engine
```

**Funciona em:**
- Início
- Atendimento
- Pedidos
- Clientes
- Campanhas
- Minha Empresa

---

## Pagination Contract

### Conversations

- ~30 mais recentes inicialmente
- Cursor pagination
- IntersectionObserver para infinite scroll

### Messages

- ~50 mais recentes ao abrir conversa
- Scroll para cima carrega anteriores
- Cursor before + prepend
- Preservar scroll anchor

**NUNCA** carregar todo o histórico inicialmente.

---

## Session Selection

**REGRAS:**

- Última sessão selecionada — reutilizar SOMENTE se ainda estiver válida/WORKING
- Se houver exatamente uma sessão WORKING — pode selecionar conscientemente
- Se houver ambiguidade ou nenhuma sessão válida — não selecionar silenciosamente

**PROIBIDO:**

```ts
workingSession || availableSessions[0]
```

---

## Referências

### Fontes Canônicas

- `docs/refoundation/GOAL.md` — Visão e princípios
- `docs/refoundation/CONTRACTS.md` — Contratos
- `INTEGRATION_GUIDE.md` — Guia de integração

### Documentação de Serviços

- `IDC_Dominuslabs/README.md` — IDPW
- `api_whatsapp_v1.2/README.md` — Whats API
