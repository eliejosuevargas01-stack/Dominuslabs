# Guia de Integração — Dominus ⇄ Serviços Externos

> **Status:** CANONICAL — Integration Guide  
> **Authority:** `docs/refoundation/GOAL.md` e `docs/refoundation/CONTRACTS.md`

Este documento descreve os contratos entre Dominus, IDPW, Whats API e n8n. Ele separa explicitamente **contratos vigentes** de **migrações planejadas**.

## 1. Dominus → IDPW

### Objetivo

Obter JWT M2M de curta duração para chamadas internas do Dominus à Whats API.

### Responsabilidade

Somente o Dominus solicita tokens M2M. O frontend não conhece o IDPW como mecanismo de autorização de negócio.

Cliente responsável:

```text
project-hub/backend/app/services/identity_client.py
```

Endpoint:

```http
POST /v1/tokens
```

Payload lógico assinado:

```json
{
  "aud": "whatsapp-api",
  "tenant_id": "tenant_123",
  "scope": "whatsapp:messages:send",
  "request_id": "<uuid>",
  "timestamp": 1900000000,
  "nonce": "<random>",
  "jti": "<uuid>"
}
```

O Dominus:

1. serializa o payload canonicamente;
2. assina com sua chave privada usando RSA PKCS#1 v1.5 + SHA-256;
3. cifra o envelope para o IDPW com AES-256-GCM + RSA-OAEP/SHA-256;
4. envia `X-Request-ID` apenas como correlação;
5. rejeita resposta plaintext ou token inválido.

O IDPW é a única autoridade M2M e publica JWKS para validação do JWT emitido.

### Scopes aceitos

```text
whatsapp:sessions:read
whatsapp:sessions:create
whatsapp:sessions:write
whatsapp:sessions:delete
whatsapp:messages:send
```

## 2. Dominus → Whats API

### Objetivo

Gerenciar recursos WhatsApp depois que o Dominus autenticou o usuário, resolveu tenant, aplicou regras de negócio e validou ownership.

Fluxo:

```text
Browser
→ Dominus
→ human auth
→ tenant
→ permission
→ session ownership
→ IDPW JWT
→ WhatsAppClient
→ Whats API
```

Cliente responsável:

```text
project-hub/backend/app/services/whatsapp_client.py
```

Regras:

- `Authorization: Bearer <JWT_M2M>`;
- `X-Request-ID` para correlação;
- `Idempotency-Key` quando aplicável;
- corpo cifrado pelo protocolo canônico;
- nenhum token M2M em banco, URL, log ou storage do browser;
- nenhuma sessão alternativa selecionada silenciosamente.

A Whats API valida JWT via JWKS, deriva `tenant_id` do token verificado e aplica namespace por tenant/sessão.

## 3. Whats API → n8n → Dominus

### Segurança vigente

Eventos entre serviços usam HMAC com timestamp e event ID. Segredos não são enviados em query string e não são reutilizados como JWT.

### Current runtime

O sistema ainda pode possuir workflows e endpoints históricos enquanto a migração é concluída.

Esses caminhos devem ser tratados como **compatibilidade temporária**, não como arquitetura final.

A fotografia dos consumidores legados está em:

```text
docs/refoundation/EVT_CATALOG.md
docs/refoundation/EVT_DEPRECATION.md
```

### Target Refoundation

O contrato canônico é `SystemEvent`:

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

Ingress planejado/canônico no Dominus:

```http
POST /api/v1/webhooks/events
```

Pipeline:

```text
Whats API
→ HMAC event
→ n8n
→ route by type
→ Dominus EventIngress
→ validation
→ idempotency
→ EventRouter
→ handler
→ persistence/realtime
```

O n8n roteia pelo `type`; ele não reconstrói arbitrariamente a semântica.

Regra crítica:

```text
message.status.updated
≠
message.created
```

Status/read/delivered/played/reaction não podem produzir notificação de nova mensagem.

## 4. Realtime para frontend

Eventos recebidos pelo Dominus devem ser publicados para uma camada realtime global da aplicação autenticada.

Target:

```text
Authenticated App
└── RealtimeProvider
    ├── event routing
    ├── deduplication
    ├── Sound Engine
    └── Notification Engine
```

O realtime não pertence ao lifecycle do `OmnichannelView`.

## 5. Mídia

A Whats API é proprietária do lifecycle de mídia.

Target:

```text
pending → downloading → ready | failed
```

Persistência:

```text
/app/data/media/{tenant}/{session}/...
```

O Dominus atua como intermediário autorizado para o frontend. O frontend não deve depender de URL temporária do WhatsApp.

## 6. Boas práticas obrigatórias

- timeout explícito em chamadas externas;
- retries apenas quando explícitos, limitados e da mesma operação;
- nenhum fallback que altere semântica;
- `X-Request-ID` é correlação, não autorização;
- erros não expõem tokens, chaves ou payloads sensíveis;
- mudanças destrutivas exigem busca de consumidores;
- distinguir sempre CURRENT RUNTIME de TARGET ARCHITECTURE;
- alterações de crypto, scope ou trust boundary exigem mudança coordenada entre os serviços.

## Referências

- `docs/architecture.md`
- `docs/refoundation/GOAL.md`
- `docs/refoundation/CONTRACTS.md`
- `docs/refoundation/EVT_CATALOG.md`
- `docs/refoundation/N8N_ROUTER_SPEC.md`
- `docs/wa-api.md`
- `IDC_Dominuslabs/README.md`
- `api_whatsapp_v1.2/README.md`
