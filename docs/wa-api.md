# Integração com Whats API

> **Status:** CANONICAL — Integration Guide

Este documento descreve como o Dominus consome a Whats API. Para a especificação completa da API, consulte `api_whatsapp_v1.2/README.md`.

---

## Visão Geral

A Whats API é o **Resource Server** WhatsApp do sistema Dominus. Ela é responsável por:
- Gerenciar sessões WhatsApp via Baileys
- Enviar e receber mensagens
- Processar mídia
- Disparar eventos para n8n

### Autenticação

Toda comunicação Dominus → Whats API utiliza **JWT M2M emitido pelo IDPW**.

**Fluxo:**

```
Dominus
  → Solicita JWT ao IDPW
  → IDPW emite JWT RS256 curto (≤300s)
  → Dominus chama Whats API com Bearer token
  → Whats API valida JWT via JWKS
```

**O browser NUNCA acessa a Whats API diretamente.**

---

## Cliente Interno

O acesso à Whats API é feito exclusivamente através de `app/services/whatsapp_client.py`.

### Endpoints Principais

| Endpoint | Método | Scope | Descrição |
|----------|--------|-------|-----------|
| `/api/sessions` | GET | `whatsapp:sessions:read` | Lista sessões |
| `/api/sessions/{id}` | GET | `whatsapp:sessions:read` | Status da sessão |
| `/api/sessions` | POST | `whatsapp:sessions:create` | Criar sessão |
| `/api/sessions/{id}/connect` | POST | `whatsapp:sessions:write` | Conectar |
| `/api/sessions/{id}/disconnect` | POST | `whatsapp:sessions:write` | Desconectar |
| `/api/sessions/{id}` | DELETE | `whatsapp:sessions:delete` | Excluir sessão |
| `/api/sessions/{id}/messages/send` | POST | `whatsapp:messages:send` | Enviar mensagem |
| `/api/sessions/{id}/media` | GET | `whatsapp:sessions:read` | Obter mídia |

---

## Headers Obrigatórios

```http
Authorization: Bearer <JWT_M2M>
X-Request-ID: <UUID>
Content-Type: application/json
Idempotency-Key: <UUID>  # Para operações mutáveis
```

---

## Criptografia de Aplicação

Dominus cifra cada corpo para a Whats API:

```json
{
  "_encrypted": true,
  "encryptedKey": "base64",
  "iv": "base64",
  "authTag": "base64",
  "payload": "base64"
}
```

### Protocolo

- AES-256-GCM para payload
- RSA-OAEP/SHA-256 para chave AES

---

## Eventos Recebidos

A Whats API dispara webhooks para n8n. O Dominus os recebe via:

### CURRENT RUNTIME

```
Whats API → n8n → POST /api/v1/webhooks/crm/update-chat
```

### TARGET (Refoundation)

```
Whats API → n8n → POST /webhooks/events (Event Ingress)
```

### Contrato de Evento

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

---

## Mídia

### Fluxo de Mídia Recebida

```
WhatsApp
  → Mensagem com mídia
  → Whats API: downloadMediaMessage()
  → Persistência em /app/data/media/{tenant}/{session}/
  → Evento para n8n com media.url
  → Dominus serve via GET /api/sessions/{session}/media
```

### Estados

| Estado | Descrição |
|--------|-----------|
| `pending` | Mídia ainda não processada |
| `downloading` | Download em andamento |
| `ready` | Arquivo disponível |
| `failed` | Falha no processamento |

### Acesso

```http
GET /api/sessions/{sessionId}/media?messageId={messageId}
Authorization: Bearer <JWT_M2M>
```

---

## Session Ownership

Dominus é responsável por:

1. Validar que a sessão pertence ao tenant atual
2. Validar que o usuário tem permissão para operar a sessão
3. NUNCA permitir operação em sessão desconectada sem ação consciente

### Validação Server-Side

```python
def validate_session_owner(tenant_id: str, session_id: str) -> Session:
    session = get_session(session_id)
    if session.tenant_id != tenant_id:
        raise ForbiddenError("Session does not belong to tenant")
    if session.status == "disconnected":
        raise ValidationError("Session is disconnected")
    return session
```

---

## Referências

### Fonte Canônica

- **`api_whatsapp_v1.2/README.md`** — Especificação completa da API

### Contratos Relacionados

- `INTEGRATION_GUIDE.md` — Guia de integração M2M
- `docs/architecture.md` — Arquitetura geral
- `docs/media-pipeline.md` — Pipeline de mídia

---

## 2. Autenticacao

Todas as requisicoes a WA API exigem autenticacao via **JWT Bearer Token**.

### Header de Autenticacao

```http
Authorization: Bearer <token>
```

### Escopos de Token

| Escopo | Descricao |
|--------|-----------|
| `whatsapp:sessions:read` | Listar sessoes, consultar status e snapshots |
| `whatsapp:sessions:create` | Criar e gerenciar sessoes (conectar, desconectar, reparar) |
| `whatsapp:messages:send` | Enviar mensagens |
| `whatsapp:media:read` | Ler e servir midias recebidas |

### Headers Obrigatorios

```http
Authorization: Bearer <token>
x-request-id: <uuid>        # UUID v4 unico por requisicao
```

### Headers Recomendados (POST de envio)

```http
Idempotency-Key: <uuid>     # Evita duplicacao de mensagens
```

### Como Obter o Token

A chave privada usada para assinar os tokens JWT esta armazenada no volume `/app/keys` do servidor da API. Tokens validos devem ser gerados por um servico autorizado interno e distribuidos aos clientes com os escopos apropriados.

---

## 3. Endpoints

| Metodo | Path | Descricao | Auth Scope | Body / Params |
|--------|------|-----------|------------|---------------|
| `POST` | `/api/sessions` | Criar nova sessao WhatsApp | `whatsapp:sessions:create` | `{ "id": "<sessionId>", "name": "..." }` |
| `GET` | `/api/sessions` | Listar todas as sessoes | `whatsapp:sessions:read` | -- |
| `GET` | `/api/sessions/:sessionId` | Status e snapshot de uma sessao | `whatsapp:sessions:read` | `sessionId` (path param) |
| `POST` | `/api/sessions/:sessionId/connect` | Iniciar conexao/gerar QR code | `whatsapp:sessions:create` | `sessionId` (path param) |
| `POST` | `/api/sessions/:sessionId/disconnect` | Desconectar sessao | `whatsapp:sessions:create` | `sessionId` (path param) |
| `POST` | `/api/sessions/:sessionId/repair-signal` | Reparar sinal/chave de sessao | `whatsapp:sessions:create` | `sessionId` (path param) |
| `POST` | `/api/sessions/:sessionId/messages/send` | Enviar mensagem | `whatsapp:messages:send` | `sessionId` (path); `{ "jid": "...", "text": "..." }` |
| `GET` | `/api/sessions/:sessionId/media` | Servir midia de mensagem | `whatsapp:media:read` | `sessionId` (path); `messageId` (query) |
| `GET` | `/api/sessions/:sessionId/health` | Health check de uma sessao | `whatsapp:sessions:read` | `sessionId` (path param) |
| `GET` | `/api/health` | Health check global da API | (publica) | -- |

---

## 4. Webhook Payload

A WA API dispara webhooks para eventos relevantes do WhatsApp. O payload segue um envelope padronizado.

### Estrutura Completa (`message.created`)

```json
{
  "tenant_id": "admin",
  "session_id": "eliezer-sc",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-09-22T14:30:00.000Z",
  "type": "message.created",
  "payload": {
    "event": "message.created",
    "session": {
      "id": "eliezer-sc",
      "name": "eliezer-sc"
    },
    "conversation": {
      "jid": "5511999999999@lid",
      "title": "Joao Silva",
      "kind": "private"
    },
    "message": {
      "id": "3EB0A1B2C3D4E5F6",
      "jid": "5511999999999@lid",
      "fromMe": false,
      "text": "Oi, tudo bem?",
      "timestamp": 1790113823,
      "type": "conversation",
      "status": "received",
      "media": null
    }
  }
}
```

### Campo `media`

Quando a mensagem contem midia (imagem, audio, video, documento), o campo `media` e um objeto em vez de `null`:

```json
{
  "media": {
    "kind": "image",
    "mimeType": "image/jpeg",
    "url": "https://whats.dominuslabs.online/api/sessions/eliezer-sc/media?messageId=3EB0A1B2C3D4E5F6"
  }
}
```

### Tipos de `conversation.kind`

| Valor | Significado |
|-------|-------------|
| `private` | Conversa individual |
| `group` | Grupo de WhatsApp |

### Tipos de `message.type`

| Valor | Significado |
|-------|-------------|
| `conversation` | Mensagem de texto simples |
| `image` | Imagem (jpg, png, webp) |
| `audio` | Audio de voz/ptt |
| `video` | Video (mp4) |
| `document` | Documento (pdf, docx, etc.) |
| `sticker` | Figurinha/sticker |

---

## 5. Seguranca do Webhook

Todas as requisicoes de webhook sao assinadas com **HMAC-SHA256** para garantir autenticidade.

### Headers de Seguranca

```http
POST /webhook HTTP/1.1
X-Webhook-Signature: sha256=abc123def456...
X-Webhook-Timestamp: 2026-09-22T14:30:00.000Z
X-Webhook-Event-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Validacao da Assinatura (Node.js)

```javascript
const crypto = require('crypto');

function verifyWebhook(payloadBody, signatureHeader, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payloadBody, 'utf8')
    .digest('hex');

  const received = signatureHeader.replace('sha256=', '');

  return crypto.timingSafeEqual(
    Buffer.from(expected, 'hex'),
    Buffer.from(received, 'hex')
  );
}
```

### Configuracao

O segredo compartilhado do webhook e definido pela variavel de ambiente `N8N_WEBHOOK_SECRET`.

---

## 6. Filtros de Webhook

A WA API aplica filtros automaticos para evitar eventos indesejados:

| Criterio | Comportamento |
|----------|--------------|
| `jid` termina com `@broadcast` | **Ignorado** - Status/Stories do WhatsApp |
| `jid` termina com `@newsletter` | **Ignorado** - Canais do WhatsApp |

Esses eventos nao disparam webhooks e nao sao propagados para consumidores.

---

## 7. URL de Midia

Midias recebidas (imagens, audios, videos, documentos) sao servidas via endpoint dedicado:

```
GET /api/sessions/{sessionId}/media?messageId={messageId}
```

### Exemplo

```
https://whats.dominuslabs.online/api/sessions/eliezer-sc/media?messageId=3EB0A1B2C3D4E5F6
```

### Requisitos

- Header `Authorization: Bearer <token>` com escopo `whatsapp:media:read`
- Header `x-request-id: <uuid>`
- A resposta retorna o arquivo binario com `Content-Type` correspondente ao `mimeType` da midia

---

## 8. Ciclo de Vida da Sessao

Uma sessao WhatsApp passa por estados bem definidos:

```
  idle          --(connect)-->  connecting
                                      |
                                      v
  disconnected  <--(fail/restart)--  qr
    ^                                      |
    |                                      v
    +--(disconnect)--------------- connected
```

| Estado | Descricao |
|--------|-----------|
| `idle` | Sessao criada, mas nao iniciada |
| `connecting` | Conectando aos servidores do WhatsApp |
| `qr` | Aguardando leitura do QR code pelo usuario |
| `connected` | Sessao ativa e pronta para enviar/receber mensagens |
| `disconnected` | Sessao desconectada (usuario saiu, falha de rede, etc.) |

### Transicoes

- `idle` -> `connecting`: chamada a `POST /api/sessions/:id/connect`
- `connecting` -> `qr`: QR code gerado, aguardando escaneamento
- `qr` -> `connected`: QR code escaneado com sucesso
- `qr` -> `disconnected`: timeout ou erro de conexao
- `connected` -> `disconnected`: chamada a `POST /api/sessions/:id/disconnect` ou perda de conexao
- `disconnected` -> `connecting`: chamada a `POST /api/sessions/:id/connect` ou `repair-signal`

---

## 9. Variaveis de Ambiente

| Variavel | Obrigatoria | Descricao |
|----------|-------------|-----------|
| `NODE_ENV` | Nao | Ambiente: `development` ou `production` |
| `PORT` | Nao | Porta da API (padrao: `3000`) |
| `N8N_WEBHOOK_SECRET` | Sim | Segredo HMAC para assinatura de webhooks |
| `JWT_PRIVATE_KEY_PATH` | Sim | Caminho da chave privada para assinar tokens (`/app/keys/...`) |
| `WEBHOOK_URL` | Sim | URL do endpoint de webhook a ser chamado |
| `REDIS_URL` | Nao | URL do Redis para cache/sessoes distribuidas |
| `LOG_LEVEL` | Nao | Nivel de log: `debug`, `info`, `warn`, `error` |

---

## 10. Exemplos de curl

### Health check (publico)

```bash
curl -X GET \
  https://whats.dominuslabs.online/api/health
```

### Criar sessao

```bash
curl -X POST \
  https://whats.dominuslabs.online/api/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)" \
  -d '{
    "id": "minha-sessao",
    "name": "Sessao Principal"
  }'
```

### Listar sessoes

```bash
curl -X GET \
  https://whats.dominuslabs.online/api/sessions \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)"
```

### Status de sessao

```bash
curl -X GET \
  https://whats.dominuslabs.online/api/sessions/minha-sessao \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)"
```

### Conectar / Gerar QR code

```bash
curl -X POST \
  https://whats.dominuslabs.online/api/sessions/minha-sessao/connect \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)"
```

### Desconectar sessao

```bash
curl -X POST \
  https://whats.dominuslabs.online/api/sessions/minha-sessao/disconnect \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)"
```

### Reparar sinal

```bash
curl -X POST \
  https://whats.dominuslabs.online/api/sessions/minha-sessao/repair-signal \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)"
```

### Enviar mensagem

```bash
curl -X POST \
  https://whats.dominuslabs.online/api/sessions/minha-sessao/messages/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "jid": "5511999999999@s.whatsapp.net",
    "text": "Ola, mundo!"
  }'
```

### Baixar midia

```bash
curl -X GET \
  "https://whats.dominuslabs.online/api/sessions/minha-sessao/media?messageId=3EB0A1B2C3D4E5F6" \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)" \
  --output midia.jpg
```

### Health check de sessao

```bash
curl -X GET \
  https://whats.dominuslabs.online/api/sessions/minha-sessao/health \
  -H "Authorization: Bearer <token>" \
  -H "x-request-id: $(uuidgen)"
```
