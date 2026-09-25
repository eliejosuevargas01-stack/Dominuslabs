# BASELINE — Dominus Product & Architecture Refoundation

> **Status:** HISTORICAL / AUDIT ARTIFACT  
> **Captured:** 2026-09-24  
> **Security note:** operational hostnames, addresses, workflow IDs and other deployment-specific identifiers were redacted after capture.  
> **Not architectural authority.** Canonical sources are `GOAL.md`, `CONTRACTS.md` and `docs/architecture.md`.

Este documento preserva uma fotografia do sistema antes do Refoundation para permitir comparação e regressão. Não deve ser atualizado para fingir que o estado histórico já correspondia ao target.

## 1. Commit baseline

| Repositório | SHA histórico | Branch/default à época |
|---|---|---|
| Dominuslabs | `9d516fd587f8f385831238152aba06ed3066315b` | `main` |
| api_whatsapp_v1.2 | `c7a05c161a32acc8742b17e5dceef23ec7c5aa92` | `main` |
| IDC_Dominuslabs | `3a63aca500a8eb09cc1c155b8b1b6edbbf5dcca9` | repository default branch |

## 2. Workflows n8n identificados

Os workflows relevantes ao baseline foram:

- Dominus AI — atendimento conversacional;
- Dominus AI Buffer — buffer/fila;
- dominuslabs_respostas_leads — ingestão/resposta de leads;
- dominuslabs_crm — workflow legado/desativado no momento da auditoria.

Os IDs reais e a URL operacional pertencem a inventário privado de operações e não ficam neste repositório público.

## 3. Variáveis de ambiente observadas

A auditoria registrou **nomes**, não valores.

### Dominus

```text
DATABASE_URL
JWT_SECRET
ADMIN_USERNAME
ADMIN_PASSWORD
ADMIN_TENANT_ID
VIEWER_USERNAME
VIEWER_PASSWORD
N8N_WEBHOOK_SECRET
N8N_TIMESTAMP_TOLERANCE_SECONDS
ENCRYPTION_MASTER_KEY
IDENTITY_WORKER_URL
WHATSAPP_API_URL
WHATSAPP_PUBLIC_URL
DOMINUS_PRIVATE_KEY
DOMINUS_PUBLIC_KEY
IDPW_PUBLIC_KEY
WHATS_API_PUBLIC_KEY
N8N_PUBLIC_KEY
```

### Whats API

```text
PG_CONNECTION_STRING
JWT_ISSUER
JWT_AUDIENCE
JWT_SUBJECT
IDPW_JWKS_URL
WHATS_API_PRIVATE_KEY
DOMINUS_PUBLIC_KEY
SESSIONS_DIR
DATA_DIR
MEDIA_DIR
N8N_WEBHOOK_URL
N8N_WEBHOOK_SECRET
```

### IDPW

```text
JWT_ISSUER
JWT_KID
JWT_WORKER_PRIVATE_KEY
WORKER_PRIVATE_KEY
DOMINUS_PUBLIC_KEY
REPLAY_KV
policy configuration
```

A lista histórica não concede autoridade a nomes legados; contratos atuais estão nos documentos canônicos dos serviços.

## 4. Superfície HTTP observada no baseline

### Dominus

Foram encontrados, entre outros, fluxos para:

- auth humana;
- CRM/conversas/histórico;
- envio de mensagens;
- webhooks inbound/callback;
- pedidos;
- produtos/cardápio;
- company settings;
- analytics;
- SSE.

### Whats API

Foram encontrados fluxos para:

- sessões;
- QR/status;
- envio de mensagens;
- mídia;
- conversas/histórico;
- webhook outbound.

### IDPW

O contrato canônico atual é:

```text
POST /v1/tokens
GET /.well-known/jwks.json
GET /health
```

Qualquer rota antiga registrada em auditorias históricas não deve ser usada como autoridade atual.

## 5. Eventos observados

Antes da unificação, a semântica era fragmentada entre WA API, n8n, endpoints do Dominus e SSE.

Exemplos de famílias observadas:

```text
message received/created
message sent
message status
session connected/disconnected
session QR
CRM update
CRM new message
order created
```

O contrato alvo/canônico é `SystemEvent`; consulte `CONTRACTS.md` e `PLAN.md`.

## 6. Suites de teste no momento do baseline

### Dominus backend

```text
204 passed
3 failed
```

As falhas eram conhecidas no domínio CRM/leads e foram registradas para separar dívida preexistente de regressão.

### Dominus frontend

```text
58 tests passed
```

### Whats API

```text
222 tests passed
```

### IDPW

```text
9 tests passed
```

Estes números são históricos e não representam o estado atual do branch.

## 7. Problemas conhecidos capturados

| # | Problema |
|---|---|
| 1 | “Pedidos Hoje” exibia histórico quando o dia estava vazio |
| 2 | Métricas de IA possuíam valores hardcoded |
| 3 | Sessão inicial podia usar fallback silencioso |
| 4 | Imagem sem expansão adequada |
| 5 | Vídeo sem viewer/fullscreen adequado |
| 6 | Sticker caía no renderer genérico |
| 7 | Avatar da sidebar usava pipeline diferente do chat |
| 8 | Realtime/notificações WhatsApp dependiam do Omnichannel montado |
| 9 | Status update podia produzir som de nova mensagem |
| 10 | Browser Notification API não existia |
| 11 | Mobile reutilizava navegação desktop adaptada |
| 12 | Drawer possuía sobreposição visual |
| 13 | Omnichannel mobile perdia área útil |
| 14 | Company Settings possuía overflow horizontal ruim |
| 15 | Project Hub aparecia para tenants |
| 16 | Meu Perfil não existia |

## 8. Estado visual histórico

### Desktop

Menu e telas ainda refletiam linguagem/admin panel anterior. Omnichannel combinava lista e chat em um grande componente.

### Mobile

Drawer lateral desktop adaptado, Omnichannel comprimido e problemas de overflow.

## 9. Monólitos identificados

No baseline foram identificados arquivos grandes nos domínios:

- Omnichannel frontend;
- Order Manager;
- Company Settings;
- webhooks backend;
- n8n service;
- session manager da Whats API.

Os números exatos de linhas pertencem à fotografia histórica; o princípio canônico é decomposição por responsabilidade, não por quantidade arbitrária de linhas.

## 10. Dependências externas

O baseline confirmou dependência de:

- IDPW;
- n8n;
- WhatsApp/Baileys;
- PostgreSQL;
- infraestrutura de containers/reverse proxy.

Endpoints, IPs, portas administrativas, IDs de container/workflow e hostnames físicos são mantidos fora da documentação pública.

## Referências atuais

- `docs/refoundation/GOAL.md`
- `docs/refoundation/CONTRACTS.md`
- `docs/refoundation/PLAN.md`
- `docs/architecture.md`
