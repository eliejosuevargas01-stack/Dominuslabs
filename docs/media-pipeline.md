# Pipeline de Mídia

> **Status:** CURRENT + TARGET MEDIA GUIDE — NON-AUTHORITY
> Este documento separa comportamento atual e arquitetura planejada. Contratos canônicos: `docs/refoundation/CONTRACTS.md` e `docs/architecture.md`.

---

## Visão Geral

A Whats API é proprietária do lifecycle da mídia do WhatsApp.

### Ownership

- **Whats API** baixa, processa, persiste e serve mídia
- **Dominus** consome mídia via endpoint autenticado
- **Frontend** nunca depende de URLs temporárias do WhatsApp

---

## CURRENT RUNTIME

### Fluxo

```
WhatsApp (mensagem com mídia)
    ↓
Baileys / Whats API
    ↓
downloadMediaMessage()
    ↓
Persistência em /app/data/media/{session}/
    ↓
Webhook para n8n com media.url
    ↓
n8n salva no banco
    ↓
Frontend carrega via Dominus → Whats API
```

### Estrutura de Diretórios

**CURRENT:**
```
/app/data/media/
├── SESSIONID1/
│   ├── FILENAME1.ext
│   └── ...
└── SESSIONID2/
    └── ...
```

### Formato do Nome de Arquivo

Formato: `JIDCLEAN_TIMESTAMP.ext`

Exemplo:
- JID: `178189703839815@lid`
- Timestamp: `1790113823`
- Arquivo: `178189703839815_lid_1790113823.jpg`

---

## TARGET ARCHITECTURE

### Estrutura Tenant-Aware

```
/app/data/media/
├── {tenant}/
│   ├── {session}/
│   │   ├── FILENAME1.ext
│   │   └── ...
│   └── ...
└── ...
```

### State Machine

```
pending → downloading → ready | failed
```

| Estado | Descrição |
|--------|-----------|
| `pending` | Mensagem recebida, mídia não processada |
| `downloading` | Download em andamento |
| `ready` | Arquivo disponível |
| `failed` | Falha no processamento |

---

## Endpoint

### Acesso

```http
GET /api/sessions/{sessionId}/media?messageId={messageId}
Authorization: Bearer <JWT_M2M>
```

### Validações

1. JWT válido via IDPW JWKS
2. Sessão pertence ao tenant
3. Mensagem pertence à sessão
4. `cachePath` dentro do diretório permitido

### Response

- Streaming do arquivo
- `Content-Type` correto
- Cache headers

---

## Tipos Suportados

| Tipo | MIME | Extensões |
|------|------|-----------|
| image | image/jpeg, image/png | .jpg, .jpeg, .png |
| video | video/mp4 | .mp4 |
| audio | audio/ogg, audio/mp3 | .ogg, .mp3 |
| document | application/pdf, etc. | .pdf, .doc, etc. |
| sticker | image/webp | .webp |

---

## Problemas Conhecidos

### T2 — n8n Salva JSON ao Invés de URL

**Problema:** n8n salva `JSON.stringify(media)` em vez de `media.url`

**Solução (Target):** Extrair apenas `media.url` antes de salvar

### T3 — Frontend Parse Incorreto

**Problema:** Frontend espera URL em `messages.media_url` mas recebe JSON string

**Solução (Target):** Contrato correto no webhook, sem necessidade de parse no frontend

---

## O que o Frontend NÃO Deve Depender

- `pps.whatsapp.net`
- `fbcdn.net`
- `directPath`
- URLs temporárias do WhatsApp

---

## Limite

Tamanho máximo por arquivo: **15MB**

---

## Referências

- `docs/architecture.md` — Arquitetura geral
- `docs/wa-api.md` — Integração com Whats API
- `api_whatsapp_v1.2/README.md` — Especificação da API
