# n8n Dominus AI - Relatório de Auditoria

**Data:** 2026-09-22 20:21:09  
**Auditor:** Hermes Agent  
**Workflows Analisados:**
- Dominus AI (ID: YqDBFFzJ1L4FRAvz)
- Dominus AI Buffer (ID: 4ANz4lSb80pCuAT4)

---

## 1. Estrutura dos Workflows

### 1.1 Dominus AI (YqDBFFzJ1L4FRAvz)

**Status:** Ativo  
**Versão:** 2957  
**Total de Nós:** 70  
**Tipos de Nós:**
- PostgreSQL: 22 nós
- Set: 10 nós
- HTTP Request: 7 nós
- If: 7 nós
- Webhook: 6 nós
- Code: 4 nós
- HTTP Request Tool: 4 nós
- Switch: 2 nós
- SerpApi: 2 nós
- Agent: 1 nó
- LM Chat OpenAI: 1 nó
- Memory Postgres Chat: 1 nó
- Execute Workflow Trigger: 1 nó
- Tool Calculator: 1 nó
- Sticky Note: 1 nó

**Pontos de Entrada:**

| Tipo | Nome | Path | Método | Autenticação |
|------|------|------|--------|--------------|
| Webhook | Dominus AI | Dominus_AI | POST | ❌ NONE |
| Webhook | Clients | clients | POST | ❌ NONE |
| Webhook | pedidos1 | pedidos | POST | ❌ NONE |
| Webhook | taxa de entrega1 | calcular_taxa_entrega | POST | ❌ NONE |
| Webhook | generate_payment2 | generate_payment | POST | ❌ NONE |
| Webhook | callback_payments | callback_payments | POST | ❌ NONE |
| Execute Workflow Trigger | select msg buffer | - | - | - |

### 1.2 Dominus AI Buffer (4ANz4lSb80pCuAT4)

**Status:** Ativo  
**Versão:** 160  
**Total de Nós:** 21  
**Tipos de Nós:**
- PostgreSQL: 7 nós
- HTTP Request: 3 nós
- Set: 3 nós
- Schedule Trigger: 2 nós
- Webhook: 2 nós
- Code: 2 nós
- Execute Workflow: 1 nó
- Switch: 1 nó

**Triggers:**
1. **Schedule Trigger** (fd0f0647-a7d0-4fdf-a8e2-000fdfb2e9bb)
   - Frequência: ❌ **A cada 1 SEGUNDO** (excessivo!)
   - Conecta a: select msg buffer

2. **Verificador de 1 em 1 Hora** (2119415f-c224-4030-999d-f745e1799f36)
   - Frequência: A cada 1 hora
   - Conecta a: Voltar para Ativo

---

## 2. Análise de Execuções (últimas 100)

### 2.1 Dominus AI

| Status | Quantidade | Porcentagem |
|--------|------------|-------------|
| Sucesso | 74 | 74% |
| Erro | 26 | 26% |

**Modos de Execução com Erro:**
- Todos os erros ocorrem em modo **"integrated"** (executado pelo Buffer)
- Webhooks externos não apresentaram erros

### 2.2 Dominus AI Buffer

| Status | Quantidade | Porcentagem |
|--------|------------|-------------|
| Sucesso | 74 | 74% |
| Erro | 26 | 26% |

**Modos de Execução com Erro:**
- Todos os erros ocorrem em modo **"trigger"** (execução agendada)

### 2.3 Correlação de Erros

**Padrão Identificado:**
- Erros em Buffer e Dominus AI ocorrem nos EXATOS mesmos timestamps
- Isso confirma relação de dependência: Buffer → Dominus AI
- Exemplos de timestamps com falhas simultâneas:
  - 23:15:00 - Erro
  - 23:14:00 - Erro
  - 23:13:00 - Erro
  - 23:09:00 - Erro
  - 23:08:30 - Erro

---

## 3. Problemas Identificados

### 🔴 CRÍTICO - SEVERIDADE ALTA

#### 3.1 Falta de Autenticação em Webhooks
**Todos os 6 webhooks do Dominus AI não possuem autenticação.**

**Risco:** Endpoints publicamente acessíveis permitem:
- Envio de mensagens não autorizadas para clientes
- Manipulação de pedidos
- Acesso a dados sensíveis de clientes
- Injeção de dados fraudulentos no sistema

**Impacto:** 
- Violação de segurança crítica
- Potencial vazamento de dados
- Manipulação do sistema por terceiros

**Recomendação:** Implementar autenticação mínima via Header Auth ou Basic Auth.

---

#### 3.2 Frequência Excessiva do Schedule Trigger
**O Schedule Trigger executa a cada 1 SEGUNDO.**

**Problemas:**
1. **Carga excessiva no banco de dados:** 86.400 queries/dia
2. **Disputa de recursos:** Duas triggers podem executar simultaneamente
3. **Erros recorrentes:** 26% das execuções falham
4. **Desperdício de recursos:** A maioria retorna "buffer vazio"

**Análise:**
- Buffer seleciona mensagens onde `data_envio < $now.minus(10 seconds)` e `processado = false`
- A query roda a cada 1 segundo, mas só processa mensagens com 10+ segundos de atraso
- Isso é contraditório e ineficiente

**Recomendação:** Diminuir frequência para 5-10 segundos com debounce.

---

### 🟠 MÉDIO - SEVERIDADE MÉDIA

#### 3.3 Falta de Tratamento para Buffer Vazio
**O workflow pode falhar quando não há mensagens para processar.**

**Evidência:**
- Taxa de erro de 26% (74/100)
- Erros ocorrem em intervalos regulares
- Possíveis race conditions

**Recomendação:** Adicionar verificação IF antes de chamar Dominus AI.

---

#### 3.4 Deduplication Key em Execuções com Erro
**Todas as execuções com erro têm deduplicationKey.**

**Análise:**
```
4ANz4lSb80pCuAT4:fd0f0647-a7d0-4fdf-a8e2-000fdfb2e9bb:2026-09-22T23:13:00.000Z
```

**Significado:**
- n8n tenta deduplicar execuções de schedule
- Mecanismo pode estar falhando
- Resulta em execuções duplicadas ou conflitantes

---

#### 3.5 Race Condition entre Triggers
**Dois triggers podem executar simultaneamente.**

**Funcionamento:**
- Schedule Trigger: a cada 1 segundo (fd0f0647-a7d0-4fdf-a8e2-000fdfb2e9bb)
- Verificador de 1 em 1 Hora: a cada hora (2119415f-c224-4030-999d-f745e1799f36)
- Trigger 2 conecta ao PostgreSQL "Voltar para Ativo"

**Possível conflito quando Triggers executam ao mesmo tempo.**

---

### 🟡 BAIXO - SEVERIDADE BAIXA

#### 3.6 Credenciais com Nomes Genéricos
**Credenciais identificadas:**
- OpenAI API: "test" (❌ nome inapropriado para produção)
- Postgres: "CuriosoTech", "dominuslabs"
- SerpApi: "SerpApi vargaseliezer112" (❌ contém informação pessoal)

---

#### 3.7 Falta de Documentação nos Nós
**Exceto por 1 Sticky Note, não há documentação inline.**

**Workflow com 70 nós precisa de:**
- Descrições emnodes críticos
- Sticky notes em seções importantes
- Comentários em código

---

## 4. Mapeamento de Conexões

### 4.1 Fluxo Principal

```
WA API Webhook
    ↓
Dominus AI (Webhook)
    ↓
Get Client (HTTP/DB)
    ↓
AI Agent (OpenAI + Memory)
    ↓
Tools/Actions
    ↓
Response to WhatsApp


Mensagem Buffered
    ↓
Buffer DB (mensagens_buffer)
    ↓
Schedule Trigger (1s)
    ↓
select msg buffer (WHERE processado=false)
    ↓
update processado=true
    ↓
Call 'Dominus AI' (Execute Workflow)
    ↓
select msg buffer (Execute Workflow Trigger)
    ↓
junta mensagens
    ↓
[continua no fluxo do Dominus AI]


Verificador de 1 em 1 Hora
    ↓
Voltar para Ativo (Postgres)
    ↓
[reseta status de mensagens?]
```

---

## 5. Recomendações Priorizadas

### PRIORIDADE 1 - IMEDIATA

1. **Implementar autenticação em todos os webhooks**
   - Usar Header Auth com API Key
   - Validar em todas as chamadas
   - Documentar método de autenticação

2. **Ajustar frequência do Schedule Trigger**
   - Mudar de 1 segundo para 5-10 segundos
   - Adicionar lógica de debounce/intervalo mínimo
   - Implementar fila com limite de concorrência

---

### PRIORIDADE 2 - CURTO PRAZO

3. **Adicionar tratamento de buffer vazio**
   - IF node após select msg buffer
   - Continuar apenas se houver mensagens
   - Registrar logs de execuções "vazias"

4. **Implementar tratamento de erros**
   - Error Trigger node
   - Retry logic com backoff
   - Notificações para erros críticos

5. **Revisar mecanismo de deduplication**
   - Verificar configuração de schedule
   - Ajustar deduplication window
   - Testar com diferentes intervalos

---

### PRIORIDADE 3 - MÉDIO PRAZO

6. **Renomear credenciais**
   - Usar nomes descritivos para produção
   - remover informação pessoal
   - Implementar rotação de secrets

7. **Adicionar documentação**
   - Sticky notes em seções principais
   - Descrições em nós críticos
   - README do workflow

8. **Implementar monitoramento**
   - Alertas para taxa de erro > 5%
   - Dashboard de execuções
   - Logs estruturados

---

### PRIORIDADE 4 - LONGO PRAZO

9. **Refatorar para arquitetura de fila**
   - Usar Redis/RabbitMQ ao invés de polling
   - Implementar consumer groups
   - Separar concerns (recebimento/processamento)

10. **Implementar testes automatizados**
    - Unit tests para código nodes
    - Integration tests para fluxos
    - Validation tests para webhooks

---

## 6. Fluxo de Dados e Arquitetura

### 6.1 Diagrama de Sequência

```
┌─────────────┐                 ┌──────────────┐                 ┌─────────────┐
│   WhatsApp  │                 │  n8n Webhook │                 │ Dominus AI  │
│     API     │                 │   Dominus    │                 │  Workflow   │
└──────┬──────┘                 └──────┬───────┘                 └──────┬──────┘
       │                               │                                 │
       │ POST /webhook/Dominus_AI      │                                 │
       ├──────────────────────────────►│                                 │
       │ (NO AUTH!)                    │                                 │
       │                               │ Get Client                      │
       │                               ├────────────────────────────────►│
       │                               │                                 │
       │                               │ AI Agent + Memory               │
       │                               ├────────────────────────────────►│
       │                               │                                 │
       │                               │ Execute Tools                   │
       │                               ├────────────────────────────────►│
       │                               │                                 │
       │  Response                     │                                 │
       │◄──────────────────────────────┤                                 │
       │                               │                                 │
       │                               │                                 │


┌─────────────┐        ┌──────────────────────┐        ┌─────────────┐
│   Buffer    │        │  Schedule Trigger    │        │ Dominus AI  │
│  Database   │        │     (every 1s)       │        │   Workflow  │
└──────┬──────┘        └──────────┬───────────┘        └──────┬──────┘
       │                          │                           │
       │ select where             │                           │
       │ processado=false         │                           │
       │◄─────────────────────────┤                           │
       │                          │                           │
       │ return messages          │                           │
       ├─────────────────────────►│                           │
       │                          │                           │
       │                          │ update processado=true    │
       │◄─────────────────────────┤                           │
       │                          │                           │
       │                          │ Execute Workflow          │
       │                          ├──────────────────────────►│
       │                          │                           │
       │                          │        (AI Processing)   │
       │                          │                           │
```

### 6.2 Tabelas do Banco de Dados

**mensagens_buffer:**
- id (number)
- tenant_id
- contact_jid
- session_id
- data_envio (timestamp)
- processado (boolean)
- [outros campos de mensagem]

**Tabelas consultadas pelo Dominus AI:**
- clients (SELECT/UPDATE)
- orders/pedidos (SELECT/INSERT/UPDATE)
- order_items (SELECT/INSERT/DELETE)
- products (SELECT)
- company_settings (SELECT)
- stock/estoque (SELECT/UPDATE)
- chat_memory (Postgres Chat Memory)

---

## 7. Conclusão

### Estado Atual
- ✅ Workflows ativos e funcionais
- ✅ Webhooks respondendo
- ⚠️ Taxa de erro de 26%
- ❌ Sem autenticação
- ❌ Frequência excessiva de polling

### Riscos Operacionais
1. **Segurança:** Alto risco de ataque/abuso
2. **Performance:** Carga desnecessária no banco
3. **Estabilidade:** Erros frequentes afetam experiência
4. **Manutenção:** Falta de documentação dificulta correções

### Próximos Passos
1. Implementar autenticação imediatamente
2. Ajustar Schedule Trigger para 10 segundos
3. Adicionar tratamento de erros
4. Monitorar taxa de erro após correções
5. Refatorar arquitetura para event-driven

---

**Fim do Relatório**

_Gerado automaticamente por Hermes Agent_
