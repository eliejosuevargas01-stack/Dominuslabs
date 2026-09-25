# Integração Dominus ↔ Whats API

> **Status:** CANONICAL — Integration Contract  
> **Authority:** `docs/refoundation/GOAL.md`, `docs/refoundation/CONTRACTS.md` e `api_whatsapp_v1.2/README.md`

Este documento descreve **somente a integração do Dominus com a Whats API**. A especificação interna da Whats API pertence ao repositório `api_whatsapp_v1.2`.

## Papel da Whats API

A Whats API é o **Resource Server WhatsApp** do ecossistema Dominus.

Responsabilidades:

- sessões Baileys;
- envio e recebimento de mensagens;
- contatos e avatares;
- estado WhatsApp;
- persistência de dados WhatsApp;
- lifecycle de mídia;
- emissão de eventos para n8n.

A Whats API **não**:

- autentica usuário humano;
- emite autoridade M2M;
- decide `tenant_id` a partir do browser;
- possui master/admin token;
- expõe private keys ao frontend.

## Trust flow

```text
Browser
  → Dominus
  → autenticação humana
  → resolve tenant
  → autorização
  → valida session ownership
  → solicita JWT M2M ao IDPW
  → WhatsAppClient
  → Whats API
  → valida JWT RS256 via JWKS
```

O browser nunca acessa a Whats API como autoridade e nunca recebe o JWT M2M.

## Cliente interno único

Chamadas do Dominus à Whats API passam pelo cliente interno:

```text
project-hub/backend/app/services/whatsapp_client.py
```

Nenhuma página React deve conhecer chaves, scopes internos ou token M2M.

## Autenticação M2M

O Dominus solicita ao IDPW um JWT curto RS256 com audience `whatsapp-api`, tenant e scope necessários.

A Whats API valida localmente:

- assinatura RS256;
- `kid`;
- issuer configurado;
- audience;
- subject;
- expiração;
- TTL;
- `tenant_id`;
- scope;
- `jti`.

A Whats API não assina esse JWT.

## Scopes congelados

| Operação | Scope |
|---|---|
| Listar/status de sessões | `whatsapp:sessions:read` |
| Criar sessão | `whatsapp:sessions:create` |
| Conectar/desconectar/alterar settings | `whatsapp:sessions:write` |
| Excluir sessão | `whatsapp:sessions:delete` |
| Enviar mensagem/mídia | `whatsapp:messages:send` |
| Avatar e mídia persistida | `whatsapp:sessions:read` |

## Headers e criptografia

Chamadas protegidas utilizam:

```http
Authorization: Bearer <JWT_M2M_IDPW>
X-Request-ID: <UUID>
Idempotency-Key: <UUID>   # quando a operação for idempotente/mutável
```

Corpos protegidos usam o envelope criptográfico canônico:

```json
{
  "_encrypted": true,
  "encryptedKey": "base64",
  "iv": "base64",
  "authTag": "base64",
  "payload": "base64"
}
```

Protocolo:

- AES-256-GCM;
- chave AES aleatória de 32 bytes;
- RSA-OAEP/SHA-256 para a chave AES;
- nenhuma aceitação de plaintext como fallback.

## Tenant e session ownership

O `tenant_id` confiável vem do contexto autenticado no Dominus e do JWT M2M validado na Whats API.

Antes de delegar uma operação, o Dominus valida que a sessão pertence ao tenant.

A Whats API mantém namespace por:

```text
(tenant_id, session_id)
```

Não existem como comportamento válido:

```text
default tenant
default session
first available session
lookup global como fallback
tenant informado pelo browser como autoridade
```

## Endpoints principais

A lista abaixo é a superfície de integração relevante ao Dominus. A especificação completa fica no README da Whats API.

| Método | Endpoint | Scope |
|---|---|---|
| GET | `/api/sessions` | `whatsapp:sessions:read` |
| GET | `/api/sessions/:sessionId` | `whatsapp:sessions:read` |
| POST | `/api/sessions` | `whatsapp:sessions:create` |
| POST | `/api/sessions/:sessionId/connect` | `whatsapp:sessions:write` |
| POST | `/api/sessions/:sessionId/disconnect` | `whatsapp:sessions:write` |
| DELETE | `/api/sessions/:sessionId` | `whatsapp:sessions:delete` |
| POST | `/api/sessions/:sessionId/messages/send` | `whatsapp:messages:send` |
| GET | `/api/sessions/:sessionId/avatar` | `whatsapp:sessions:read` |
| GET | `/api/sessions/:sessionId/media?messageId=...` | `whatsapp:sessions:read` |

## Eventos — CURRENT vs TARGET

### Current runtime

Enquanto consumidores legados ainda existirem, alguns fluxos podem continuar passando por endpoints históricos e workflows n8n específicos. Eles não são a arquitetura canônica futura.

Consulte:

- `docs/refoundation/EVT_CATALOG.md` — fotografia histórica;
- `docs/n8n-workflows.md` — separação CURRENT/TARGET.

### Target Refoundation

O contrato assíncrono canônico é:

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

Tipos iniciais:

```text
message.created
message.status.updated
message.reaction.updated
conversation.updated
media.processing
media.ready
media.failed
session.connected
session.disconnected
session.qr.updated
order.created
order.updated
order.cancelled
```

Semântica não pode mudar durante o pipeline. Em especial, `message.status.updated` nunca pode ser convertido em `message.created`.

## Mídia

A Whats API é proprietária do lifecycle de mídia.

Target:

```text
message persisted
  → pending
  → downloading
  → ready | failed
```

Storage alvo:

```text
/app/data/media/{tenant}/{session}/...
```

O frontend não depende de `pps.whatsapp.net`, `fbcdn.net`, `directPath` ou URL temporária do WhatsApp.

O endpoint de leitura deve servir mídia já persistida. Recuperação/retry, quando disponível, deve ser explícita, limitada e observável — nunca um fallback silencioso do GET.

## Referências

- `docs/architecture.md` — arquitetura global;
- `docs/refoundation/GOAL.md` — visão;
- `docs/refoundation/CONTRACTS.md` — invariantes;
- `INTEGRATION_GUIDE.md` — contratos entre sistemas;
- `docs/media-pipeline.md` — lifecycle de mídia;
- `api_whatsapp_v1.2/README.md` — especificação canônica do Resource Server.
