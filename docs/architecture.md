# Arquitetura do DominusLabs

Este documento descreve a arquitetura do sistema DominusLabs, que integra comunicação via WhatsApp com um backend em Python e frontend React para gerenciamento de leads e atendimento omnichannel.

## Diagrama da Arquitetura

```
                   ┌──────────────┐
                   │   WhatsApp   │
                   └─────┬──────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
    ┌─────▼─────┐           ┌─────────▼─────────┐
    │ WA API    │           │   n8n             │
    │ (Node.js) │           │ (self-hosted v2.37)│
    └─────┬─────┘           └─────────▲─────────┘
          │                       │
          │         ┌───────────▼───────────┐
          │         │   PostgreSQL (WA)   │
          │         │  (72.60.247.157:5430)│
          │         └─────────▲───────────┘
          │                   │
          │        ┌──────────▼──────────┐
          │        │   Backend API       │
          │        │  (FastAPI + Python) │
          └────────▼─────────────────────┘
                ┌──▼──┐
                │SSE  │
                │Front│
                └──▲──┘
                   │
        ┌──────────▼──────────┐
        │   Frontend          │
        │ (React + TypeScript)│
        └─────────────────────┘
```

## Tabela de Serviços

| Nome       | Tecnologia       | Porta      | URL                        | Função                                       |
|------------|------------------|------------|----------------------------|----------------------------------------------|
| Backend    | FastAPI + Python | 443 (HTTPS)| https://dominuslabs.online | API principal, SSE events                    |
| WA API     | Node.js + Fastify| 3000       | https://whats.dominuslabs.online | Gerencia comunicação com WhatsApp          |
| n8n        | Self-hosted      | 8080       | https://myn8n.seommerce.shop | Workflows de automação                       |
| PostgreSQL | PostgreSQL 15    | 5432       | lqxr1id9xont55qcla197k8f   | Banco de dados principal do backend          |
| PostgreSQL | PostgreSQL 15    | 5430       | 72.60.247.157:5430         | Banco de dados específico para WA API        |

## Fluxo de Mensagem Recebida (WhatsApp → Frontend)

1. WhatsApp envia uma mensagem para o WA API via WebSocket
2. WA API baixa mídia (se houver) e salva em `/app/data/media/`
3. WA API dispara webhook HTTP POST para n8n (`dominuslabs_respostas_leads`)
4. n8n valida HMAC, salva no banco PostgreSQL (tabelas: `messages`, `conversations`, `contacts`)
5. n8n chama POST `/api/v1/webhooks/crm/update-chat` no backend
6. Backend emite evento SSE para clientes conectados
7. Frontend `OmnichannelView.tsx` recebe SSE e atualiza chat em tempo real

## Fluxo de Mensagem Enviada (Frontend → WhatsApp)

1. Frontend faz requisição POST para `/api/v1/crm/messages/send`
2. Backend envia requisição POST para `https://whats.dominuslabs.online/api/sessions/{id}/messages/send` (com JWT)
3. WA API utiliza Baileys `socket.sendMessage()` para enviar mensagem ao WhatsApp
4. Baileys retorna confirmação ao WA API, que dispara webhook com `fromMe=true`
5. O webhook segue o mesmo fluxo da mensagem recebida

## Autenticação entre Serviços

- **Frontend** usa JWT Bearer token (autenticação via `/api/v1/auth/login`)
- **Backend ↔ WA API**: JWT com escopos (ex: `whatsapp:messages:send`) assinados por chave interna
- **n8n ↔ Backend**: HMAC-SHA256 via header `X-N8N-Signature`

## Volumes Persistentes

- `/app/sessions`: Credenciais Baileys (credenciais de sessão)
- `/app/data`: Mídia baixada, mensagens em JSON, dados das conversas
- `/app/keys`: Chaves JWT para autenticação interna

## Variáveis de Ambiente Críticas

### Backend API
- `DATABASE_URL`: URL de conexão com PostgreSQL principal
- `JWT_SECRET_KEY`: Chave secreta para geração de tokens JWT
- `WA_API_URL`: URL do serviço WA API para envio de mensagens
- `N8N_WEBHOOK_SECRET`: Segredo para validação HMAC do n8n

### WA API
- `DATABASE_URL`: URL de conexão com PostgreSQL específico do WA API
- `JWT_SECRET_KEY`: Chave secreta de autenticação entre backend e WA API
- `SESSIONS_DIR`: Diretório de sessões Baileys
- `MEDIA_DIR`: Diretório para armazenamento de mídia

### n8n
- `N8N_WEBHOOK_SECRET`: Segredo para validação de webhooks do Dominus Labs
- `DATABASE_URL`: URL de conexão com PostgreSQL (se usado diretamente)

## Banco de Dados

### Tabelas Principais

- `messages`: Armazena mensagens recebidas/registradas
- `conversations`: Conversas entre usuários e representantes
- `contacts`: Informações dos contatos no WhatsApp
- `sessions`: Estados de sessões do WhatsApp (tokens, configurações)