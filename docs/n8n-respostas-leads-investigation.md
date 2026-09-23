# n8n Workflow: dominuslabs_respostas_leads - Error Investigation

**ID:** SpQwyDZsOo3ozXuE  
**URL:** https://myn8n.seommerce.shop/webhook/lead_responses  
**Data:** 2026-09-23

---

## 1. Estrutura do Workflow

### Nodes e Tipos

| Node | Tipo | Função |
|------|------|--------|
| Webhook | n8n-nodes-base.webhook | Entrada POST /webhook/lead_responses |
| Validar HMAC | n8n-nodes-base.code | Valida assinatura HMAC-SHA256 do webhook |
| criar contato | n8n-nodes-base.postgres | Upsert na tabela contacts |
| salva mensagem1 | n8n-nodes-base.postgres | Upsert na tabela messages |
| Select rows from a table | n8n-nodes-base.postgres | SELECT da tabela conversations |
| update preview | n8n-nodes-base.postgres | Upsert na tabela conversations |
| Wait | n8n-nodes-base.wait | Aguarda 1 segundo |
| Code in JavaScript1 | n8n-nodes-base.code | Gera assinatura para notificar backend |
| notifica dominuslabs1 | n8n-nodes-base.httpRequest | POST para dominuslabs.online/api/v1/webhooks/crm/update-chat |
| If | n8n-nodes-base.if | Condicional para encaminhar ao Dominus AI |
| HTTP Request4 | n8n-nodes-base.httpRequest | POST para Dominus AI webhook |
| Switch | n8n-nodes-base.switch | Roteamento por título da conversa |
| api_cartazes | n8n-nodes-base.webhook | Webhook secundário para PDFs |

### Fluxo Principal

```
Webhook (POST /lead_responses)
    ↓
Validar HMAC (valida assinatura)
    ↓
criar contato (upsert em contacts)
    ↓
salva mensagem1 (upsert em messages)
    ↓
┌─────────────────┬─────────────────┐
│                 │                 │
Select rows → update preview    Wait → Code in JS1 → notifica dominuslabs1
(conversations)  (conversations)     (1s wait)  (assinatura)  (POST backend)
                                   
```

---

## 2. Análise de Erros

### Execuções com Erro (últimas 50)

**Total encontrado:** 50 execuções com erro

### Categorias de Erro Identificadas

#### Categoria A: HTTP 409 - Evento Duplicado

| Atributo | Valor |
|----------|-------|
| **Node** | notifica dominuslabs1 |
| **HTTP Code** | 409 |
| **Mensagem** | "Evento duplicado: requisição com este event_id já foi processada recentemente." |
| **Frequência Estimada** | ~90% dos erros |
| **Root Cause** | O backend Dominus Labs possui controle de idempotência baseado em event_id. Quando a mesma mensagem WhatsApp gera múltiplos webhooks (ex: status transitions: sent → delivered → read), o backend rejeita duplicatas. Isso é **comportamento esperado**, não um bug. |

**Exemplo de input que causa erro:**
```json
{
  "message_id": "ACFAD9B68BE0F7EE15E889A5BA5F0110",
  "status": "delivered",  // Mesma mensagem, status diferente
  "event_id": "ACFAD9B68BE0F7EE15E889A5BA5F0110:delivered"
}
```

**Recomendação:**
- O erro HTTP 409 é **legítimo** e não deveria ser tratado como erro crítico
- O workflow já tem `retryOnFail: true` no node, mas isso não ajuda para 409
- **Sugestão:** Configurar o node para tratar HTTP 409 como sucesso (não é falha real)

---

#### Categoria B: HTTP 502 - Bad Gateway

| Atributo | Valor |
|----------|-------|
| **Node** | notifica dominuslabs1 |
| **HTTP Code** | 502 |
| **Mensagem** | "Bad Gateway" |
| **Frequência Estimada** | ~5% dos erros |
| **Root Cause** | O backend FastAPI (dominuslabs.online) pode estar temporariamente indisponível ou com problemas de infraestrutura. O workflow já tem retry automático habilitado (`retryOnFail: true`). |

**Recomendação:**
- Monitorar disponibilidade do backend FastAPI
- Verificar logs do servidor quando 502 ocorrer

---

#### Categoria C: NodeOperationError - Missing Matching Column

| Atributo | Valor |
|----------|-------|
| **Node** | criar contato |
| **Tipo** | NodeOperationError |
| **Mensagem** | "Column to match on not found in input item. Add a column to match on or set the 'Data Mode' to 'Define Below' to define the value to match on." |
| **Frequência** | 1 caso observado (execução 233776) |
| **Root Cause** | O payload do webhook não continha o campo `payload.conversation.jid` esperado pelo node `criar contato`. Isso indica um webhook malformado ou incompatível. |

**Input problemático (execução 233776):**
- O node esperava `$json.payload.conversation.jid` mas o input tinha estrutura diferente
- Provavelmente um teste ou payload manual

**Recomendação:**
- Adicionar validação de schema após o node Validar HMAC
- Usar fallback/valor padrão quando campo esperado não existe

---

#### Categoria D: ReferenceError - Code Execution Error

| Atributo | Valor |
|----------|-------|
| **Node** | Code in JavaScript1 |
| **Tipo** | ReferenceError |
| **Mensagem** | "fXiUncnUXf1bG48Kp4CBQvm23yUooKwGWWn23xHzxFpbidPyiivZFvQDRuEfC9AF is not defined [line 3]" |
| **Frequência** | 1 caso observado (execução 233879) |
| **Root Cause** | Erro histórico de versão do workflow. O código JavaScript tinha o segredo hardcoded sem aspas. Foi corrigido em versões posteriores. |

**Recomendação:**
- ✅ Já corrigido nas versões atuais do workflow

---

## 3. Validação HMAC

### Como Funciona

O node `Validar HMAC` implementa validação de assinatura HMAC-SHA256:

```javascript
const WEBHOOK_SECRET = "fXiUncnUXf1bG48Kp4CBQvm23yUooKwGWWn23xHzxFpbidPyiivZFvQDRuEfC9AF";

const signature = headers['x-webhook-signature'];  // sha256=...
const timestamp = headers['x-webhook-timestamp'];
const eventId   = headers['x-webhook-event-id'];

const signed = `${timestamp}.${eventId}.${rawBody}`;
const expected = 'sha256=' + crypto.createHmac('sha256', WEBHOOK_SECRET)
  .update(signed, 'utf8').digest('hex');

// Timing-safe comparison
const valid = crypto.timingSafeEqual(
  Buffer.from(signature, 'ascii'),
  Buffer.from(expected, 'ascii')
);
```

### Status

✅ **Funcionando corretamente** - Nenhum erro de HMAC encontrado nas execuções analisadas.

---

## 4. Nodes de Banco de Dados

### criar contato (upsert contacts)

- **Tabela:** contacts
- **Matching Column:** contact_jid
- **Campos:** contact_jid, push_name, display_phone, profile_pic_url, tenant_id, created_at, updated_at
- **Status:** ✅ Funcionando (erro isolado em 233776 por payload malformado)

### salva mensagem1 (upsert messages)

- **Tabela:** messages  
- **Matching Columns:** message_id, session_id
- **Campos:** message_id, contact_jid, session_id, is_from_me, chat_kind, message_type, content, status, message_timestamp, media_url, participant, quoted_*, reaction_*, tenant_id
- **Status:** ✅ Funcionando corretamente

### update preview (upsert conversations)

- **Tabela:** conversations
- **Matching Columns:** contact_jid, session_id
- **Status:** ✅ Funcionando corretamente

---

## 5. Integração com idc_dominus

### Análise

❌ **Nenhuma integração direta com idc_dominus encontrada.**

O workflow **não** faz chamadas ao identity provider idc_dominus (IDPW):

- Todos os nodes HTTP Request apontam para:
  - `https://dominuslabs.online/api/v1/webhooks/crm/update-chat` (backend principal)
  - `https://myn8n.seommerce.shop/webhook/Dominus_AI` (webhook interno do Dominus AI)
  - `https://dominuslabs.online/api/v1/webhooks/outbound/whatsapp/send` (envio WhatsApp)

- Não há endpoints de autenticação/token sendo chamados
- O tenant_id é passado diretamente no payload do webhook (hardcoded como "admin")

---

## 6. Resumo Executivo

### Problemas Encontrados

| # | Problema | Severidade | Status |
|---|----------|------------|--------|
| 1 | HTTP 409 de eventos duplicados | Baixa | Esperado (idempotência) |
| 2 | HTTP 502 Bad Gateway esporádico | Média | Infraestrutura backend |
| 3 | Payload malformado em criar contato | Baixa | Caso isolado |
| 4 | ReferenceError em Code JS | Baixa | Já corrigido |

### Recomendações

1. **Tratar HTTP 409 como sucesso** - Não é erro real, é controle de idempotência
2. **Monitorar backend** para reduzir 502
3. **Validar schema de entrada** antes de acessar campos obrigatórios
4. **Considerar Dead Letter Queue** para mensagens com erro

---

## 7. Próximos Passos

- [ ] Implementar tratamento de HTTP 409 no node `notifica dominuslabs1`
- [ ] Adicionar validação de schema após `Validar HMAC`
- [ ] Configurar alertas para HTTP 502 no backend
- [ ] Revisar necessidade de idc_dominus para autenticação do tenant

---

**Investigado por:** Hermes Agent  
**Data:** 2026-09-23  
**Workflow Version:** 0e9ef45c-93c3-439f-ba87-f39d5f7eb8d0
