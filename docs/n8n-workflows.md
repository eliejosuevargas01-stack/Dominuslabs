# Workflows n8n — DominusLabs

Este documento descreve os workflows executados no n8n da instância `myn8n.seommerce.shop`, seu papel na arquitetura e os fluxos de dados entre WhatsApp, banco de dados, backend e agente de IA.

---

## 1. Visão Geral

O n8n atua como **orquestrador de eventos** no meio do fluxo de mensagens do DominusLabs:

1. Recebe webhooks da **WA API** (mensagens enviadas/recebidas via WhatsApp).
2. Valida segurança via **HMAC**.
3. Persiste dados no **PostgreSQL** (tabelas `contacts`, `messages`, `conversations`).
4. Notifica o **backend** em tempo real via SSE (`/api/v1/webhooks/crm/update-chat`).
5. Encaminha mensagens recebidas de clientes para o agente **Dominus AI**, que processa e responde automaticamente.

---

## 2. Workflows

| ID | Nome | Status | Função |
|---|---|---|---|
| `SpQwyDZsOo3ozXuE` | `dominuslabs_respostas_leads` | Ativo | Recebe webhook do WA API, valida HMAC, salva mensagem no banco, notifica frontend e encaminha para Dominus AI |
| `WJ37gGiodnAJVkBN` | `dominuslabs_crm` | Ativo | Legado — função a ser verificada. Pode conter lógica antiga do CRM que será consolidada ou removida. |
| `YqDBFFzJ1L4FRAvz` | `Dominus AI` | Ativo | Agente de IA que processa mensagens recebidas e gera respostas automáticas via WhatsApp |
| `4ANz4lSb80pCuAT4` | `Dominus AI Buffer` | Ativo | Buffer / fila para o workflow `Dominus AI`, gerenciando concorrência e taxa de requisições |

---

## 3. Fluxo Detalhado: `dominuslabs_respostas_leads`

Passo a passo de cada nó do workflow ativo de recebimento de mensagens:

| Ordem | Nó | Tipo | Descrição |
|---|---|---|---|
| 1 | Webhook Trigger | Webhook | Recebe POST da WA API no endpoint `/webhook/lead_responses` |
| 2 | Validar HMAC | Code / Function | Verifica assinatura `X-Webhook-Signature` usando o HMAC secret configurado por sessão |
| 3 | criar contato | Postgres | Faz **upsert** na tabela `contacts` (insere ou atualiza o contato pelo `contact_jid`) |
| 4 | salva mensagem1 | Postgres | Faz **upsert** na tabela `messages` com os dados da mensagem recebida |
| 5 | update preview | Postgres | Faz **upsert** na tabela `conversations`, atualizando `last_message_preview` e timestamp |
| 6 | Wait | Wait | Aguarda breve intervalo antes de notificar o backend |
| 7 | Code in JavaScript1 | Code Node | Gera assinatura HMAC para o backend DominusLabs |
| 8 | notifica dominuslabs1 | HTTP Request | Faz POST para `/api/v1/webhooks/crm/update-chat` com payload da mensagem |
| 9 | If | IF | Verifica condições (ex: mensagem não é `fromMe`) |
| 10 | HTTP Request4 | HTTP Request | Se a condição do `If` for satisfeita, encaminha mensagem para o workflow **Dominus AI** |

---

## 4. Segurança: Validação HMAC

A comunicação entre WA API, n8n e backend utiliza **HMAC-SHA256** para garantir autenticidade dos payloads.

### 4.1 WA API → n8n
- A WA API envia o header `X-Webhook-Signature` com o HMAC do payload.
- O nó **Validar HMAC** recalcula a assinatura usando o `secret` configurado na sessão e compara com o header recebido.
- Se inválido, a execução é interrompida.

### 4.2 n8n → Backend
- O nó **Code in JavaScript1** gera uma nova assinatura HMAC para o payload enviado ao backend.
- O backend valida essa assinatura ao receber a requisição em `/api/v1/webhooks/crm/update-chat`.

> **Importante:** O HMAC secret é configurado por sessão de WhatsApp e deve ser idêntico tanto na WA API quanto no n8n.

---

## 5. Banco de Dados

O workflow `dominuslabs_respostas_leads` escreve nas seguintes tabelas do PostgreSQL (banco `DOMINUS_DB`):

### 5.1 `messages`
| Campo | Descrição |
|---|---|
| `message_id` | ID único da mensagem (vindo da WA API) |
| `contact_jid` | Identificador JID do contato |
| `session_id` | ID da sessão de WhatsApp |
| `content` | Texto da mensagem |
| `is_from_me` | Booleano — `true` se a mensagem foi enviada pelo número do DominusLabs |
| `media_url` | URL do arquivo de mídia, caso exista |
| `status` | Status da mensagem (ex: `sent`, `delivered`, `read`) |
| `message_timestamp` | Timestamp de recebimento/envio |
| `tenant_id` | ID do tenant (multi-tenant) |

### 5.2 `conversations`
| Campo | Descrição |
|---|---|
| `contact_jid` | Identificador JID do contato (chave primária / única por sessão) |
| `session_id` | ID da sessão de WhatsApp |
| `last_message_preview` | Prévia do texto da última mensagem (para lista de chats) |
| `last_message_timestamp` | Timestamp da última mensagem |
| `unread_count` | Contador de mensagens não lidas |
| `tenant_id` | ID do tenant |

### 5.3 `contacts`
| Campo | Descrição |
|---|---|
| `contact_jid` | Identificador JID do contato |
| `push_name` | Nome de exibição vindo do WhatsApp |
| `display_phone` | Número de telefone formatado |
| `profile_pic_url` | URL da foto de perfil, se disponível |
| `tenant_id` | ID do tenant |

---

## 6. Fluxo de Encaminhamento para Dominus AI

Quando uma mensagem recebida **não é do próprio sistema** (`fromMe = false`), o workflow a encaminha para processamento automático:

```
WhatsApp (cliente)
    ↓
Baileys / WA API
    ↓
POST /webhook/lead_responses  →  n8n (dominuslabs_respostas_leads)
    ↓ (se fromMe = false)
POST para Dominus AI (workflow YqDBFFzJ1L4FRAvz)
    ↓
Dominus AI processa e decide resposta
    ↓
POST /api/v1/webhooks/outbound/whatsapp/send
    ↓
Mensagem enviada ao cliente via WhatsApp
```

O workflow **Dominus AI Buffer** (`4ANz4lSb80pCuAT4`) atua como fila intermediária para evitar sobrecarga do modelo de IA e garantir que as respostas sejam enviadas na ordem correta.

---

## 7. Configuração de Webhook na WA API

Para que as mensagens cheguem ao n8n, cada sessão de WhatsApp deve ter o seguinte webhook configurado na WA API:

| Parâmetro | Valor |
|---|---|
| **URL** | `https://myn8n.seommerce.shop/webhook/lead_responses` |
| **Evento** | `message.created` |
| **HMAC Secret** | Configurado por sessão (deve corresponder ao usado no nó de validação do n8n) |
| **Habilitado** | `enabled = true` (obrigatório) |
| **Filtros** | Descarta mensagens de `@broadcast` e `@newsletter` |

> **Nota:** O descarte de `@broadcast` e `@newsletter` evita que mensagens de status e canais poluam o CRM e disparem respostas automáticas da IA.

---

## 8. Nota sobre `dominuslabs_crm`

O workflow `dominuslabs_crm` (`WJ37gGiodnAJVkBN`) está **ativo** mas sua função atual é **desconhecida**. Ele pode conter lógica legada do CRM que já foi migrada para o fluxo principal `dominuslabs_respostas_leads`.

**Recomendação:**
- Revisar os nós e execuções recentes deste workflow.
- Determinar se ainda é necessário ou pode ser desativado.
- Documentar a função real após auditoria.

---

## 9. Variáveis e Credenciais Necessárias no n8n

### 9.1 Credenciais de Banco de Dados
| Credencial | Tipo | Uso |
|---|---|---|
| `DOMINUS_DB` | PostgreSQL | Conexão com o banco de dados principal para upserts nas tabelas `contacts`, `messages` e `conversations` |

### 9.2 Variáveis / Segredos por Sessão
| Variável | Descrição |
|---|---|
| `HMAC_SECRET` | Chave secreta usada para validar a assinatura do webhook vindo da WA API e para assinar requisições ao backend |

### 9.3 Parâmetros de Acesso ao Backend
| Parâmetro | Valor / Descrição |
|---|---|
| URL do backend | `https://<dominio>/api/v1/webhooks/crm/update-chat` |
| Método | `POST` |
| Headers | `X-Webhook-Signature` (gerado pelo nó de código JavaScript) |

### 9.4 Variáveis do Workflow Dominus AI
| Parâmetro | Descrição |
|---|---|
| URL do workflow Dominus AI | Endpoint interno ou webhook do workflow `YqDBFFzJ1L4FRAvz` |
| Token / Chave de API | Se necessário para autenticar entre workflows n8n |

---

## 10. Resumo do Fluxo Completo de Mensagem Recebida

```
WhatsApp (mensagem do cliente)
    ↓
Baileys
    ↓
WA API (evento message.created)
    ↓
POST https://myn8n.seommerce.shop/webhook/lead_responses
    ↓
n8n: dominuslabs_respostas_leads
  ├── Valida HMAC
  ├── Upsert PostgreSQL (contacts, messages, conversations)
  ├── Notifica backend via /api/v1/webhooks/crm/update-chat (SSE)
  └── Se não fromMe → encaminha para Dominus AI
    ↓
Dominus AI → gera resposta
    ↓
POST /api/v1/webhooks/outbound/whatsapp/send
    ↓
Mensagem enviada ao cliente
```
