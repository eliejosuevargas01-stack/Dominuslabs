# Auditoria de Documentação — Dominus Ecosystem

> **Status:** AUDIT REPORT
> **Data:** 2026-09-25
> **Escopo:** Dominuslabs, IDC_Dominuslabs, api_whatsapp_v1.2

---

## Sumário Executivo

Esta auditoria classifica todos os documentos dos 3 repositórios do ecossistema Dominus. O objetivo é preparar o saneamento documental conforme o **Refoundation Plan**.

---

## 1. FONTES CANÔNICAS PRINCIPAIS

| Arquivo | Repo | Status | Descrição |
|---------|------|--------|-----------|
| `docs/refoundation/GOAL.md` | dominuslabs | CANONICAL | Visão e princípios da refoundation |
| `docs/refoundation/CONTRACTS.md` | dominuslabs | CANONICAL | Contratos de arquitetura |
| `docs/refoundation/PLAN.md` | dominuslabs | CURRENT_PLAN | Plano de implementação |
| `TASKS.md` | dominuslabs | CURRENT_PLAN | Backlog de tasks |
| `IDC_Dominuslabs/README.md` | idc-dominuslabs | CANONICAL | Documentação do IDPW |
| `api_whatsapp_v1.2/README.md` | api-whatsapp-service | CANONICAL | Documentação da Whats API |
| `INTEGRATION_GUIDE.md` | dominuslabs | CANONICAL | Guia de integração M2M |

---

## 2. DOCUMENTOS REESCREVER COMPLETAMENTE

### 2.1 `docs/architecture.md` — REWRITE

**Problemas identificados:**
- Contém IP real: `72.60.247.157:5430`
- Descreve autenticação M2M antiga (JWT_SECRET_KEY entre Backend ↔ WA API)
- Confia em tenant_id do browser
- Não menciona IDPW como autoridade M2M
- Fluxo n8n descrito como arquitetura oficial sem distinção CURRENT/TARGET
- Não representa EventIngress nem RealtimeProvider

**Ação:** Reescrever completamente representando a arquitetura canônica do GOAL.md

---

### 2.2 `docs/frontend-omnichannel.md` — REWRITE

**Problemas identificados:**
- Contém fallback proibido de sessão: `availableSessions[0]`
- Documenta SSE montado somente quando Omnichannel está aberto
- Descreve monólito como arquitetura
- Não separa features/omnichannel/ de realtime/

**Ação:** Reescrever descrevendo arquitetura alvo por feature

---

### 2.3 `docs/wa-api.md` — REWRITE

**Problemas identificados:**
- Descreve scopes antigos (`whatsapp:media:read`)
- Documenta JWT_SECRET_KEY como mecanismo de autenticação
- Não menciona IDPW nem JWKS
- Contém URL real: `whats.dominuslabs.online`
- Duplica especificação que deveria estar no README da Whats API

**Ação:** Reescrever como visão de integração do ponto de vista do Dominus

---

### 2.4 `docs/n8n-workflows.md` — REWRITE

**Problemas identificados:**
- Documenta pipeline legado como arquitetura principal
- Não distingue CURRENT de TARGET
- Contém URLs reais: `myn8n.seommerce.shop`
- Workflow IDs expostos

**Ação:** Reescrever distinguindo current runtime de target event contract

---

### 2.5 `README.md` — REWRITE

**Problemas identificados:**
- É o template Vite padrão
- Não representa o produto
- Nenhuma informação útil sobre Dominus

**Ação:** Reescrever como índice e descrição do produto

---

### 2.6 `docs/deployment.md` — REWRITE + SECURITY CLEANUP

**Problemas identificados:**
- Contém IP real: `72.60.247.157`
- Contém porta SSH real: `2222`
- Contém usuário SSH: `root`
- Contém container IDs
- Contém App IDs
- Contém URLs operacionais privadas
- Contém comandos específicos de infraestrutura real

**Ação:** Reescrever como documentação genérica de deployment. Remover todos os dados operacionais reais.

---

### 2.7 `api_whatsapp_v1.2/ARCHITECTURE.md` — REWRITE

**Problemas identificados:**
- Documenta proposta histórica de modularização
- Não reflete o target do Refoundation
- Deveria distinguir CURRENT de TARGET

**Ação:** Reescrever refletindo arquitetura alvo

---

## 3. DOCUMENTOS PARCIALMENTE CORRETOS

### 3.1 `docs/media-pipeline.md` — PARTIAL UPDATE

**Preservar:**
- Fluxo de download/persistência
- Endpoint de mídia

**Corrigir:**
- Caminho `/app/data/media/SESSION` → `/app/data/media/{tenant}/{session}`
- State machine: pending → downloading → ready → failed
- Remover JSON.parse como solução

---

### 3.2 `INTEGRATION_GUIDE.md` — PRESERVE + MINOR UPDATE

**Status:** Majoritariamente correto
**Ação:** Atualizar seções de events para refletir target contract

---

## 4. DOCUMENTOS CANÔNICOS A PRESERVAR

| Arquivo | Status | Ação |
|---------|--------|------|
| `docs/refoundation/GOAL.md` | CANONICAL | Preservar |
| `docs/refoundation/CONTRACTS.md` | CANONICAL | Preservar |
| `docs/refoundation/BASELINE.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/FALLBACK_AUDIT.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/EVT_CATALOG.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/CHECKPOINT_ARCH.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/CHECKPOINT_DATA.md` | HISTORICAL | Adicionar banner |
| `IDC_Dominuslabs/README.md` | CANONICAL | Preservar |
| `api_whatsapp_v1.2/README.md` | CANONICAL | Preservar |

---

## 5. PROBLEMAS DE SEGURANÇA IDENTIFICADOS

| Arquivo | Tipo | Localização | Ação |
|---------|------|-------------|------|
| `docs/architecture.md` | IP público | `72.60.247.157:5430` | Remover |
| `docs/deployment.md` | IP público | `72.60.247.157` | Remover |
| `docs/deployment.md` | Porta SSH | `2222` | Remover |
| `docs/deployment.md` | Usuário SSH | `root` | Remover |
| `docs/deployment.md` | Container IDs | `sjrweu7rw8e3nywm5stef2ri`, `hkossco0sggwwwss0cwk4w0s` | Remover |
| `docs/deployment.md` | App IDs | `38`, `32` | Remover |
| `docs/deployment.md` | URLs operacionais | `myn8n.seommerce.shop` | Remover |
| `docs/wa-api.md` | URL real | `whats.dominuslabs.online` | Usar placeholder |
| `docs/n8n-workflows.md` | URLs reais | `myn8n.seommerce.shop` | Remover |
| `docs/n8n-workflows.md` | Workflow IDs | `SpQwyDZsOo3ozXuE`, etc. | Remover |

---

## 6. CONTRADIÇÕES ENCONTRADAS

### 6.1 Autenticação M2M

| Documento | Versão |
|-----------|--------|
| `docs/architecture.md` | JWT_SECRET_KEY entre Backend ↔ WA API |
| `docs/wa-api.md` | JWT_SECRET_KEY como mecanismo |
| `INTEGRATION_GUIDE.md` | IDPW como autoridade M2M ✅ |
| `api_whatsapp_v1.2/README.md` | IDPW + JWKS ✅ |

**Contradição:** Documentos antigos descrevem JWT interno, fontes canônicas descrevem IDPW.

---

### 6.2 Session Fallback

| Documento | Versão |
|-----------|--------|
| `docs/frontend-omnichannel.md` | `workingSession || availableSessions[0]` |
| `docs/refoundation/GOAL.md` | Fallback proibido |

**Contradição:** Documento documenta comportamento proibido como válido.

---

### 6.3 Event Semantics

| Documento | Versão |
|-----------|--------|
| `docs/n8n-workflows.md` | n8n upsert DB + chama backend |
| `docs/refoundation/GOAL.md` | EventIngress unificado |

**Contradição:** Pipeline antigo documentado como arquitetura oficial.

---

## 7. MATRIZ DE CLASSIFICAÇÃO

### Dominuslabs

| Arquivo | Status | Ação |
|---------|--------|------|
| `README.md` | REWRITE | Reescrever completamente |
| `INTEGRATION_GUIDE.md` | CANONICAL | Preservar + minor update |
| `docs/architecture.md` | REWRITE | Reescrever completamente |
| `docs/deployment.md` | REWRITE | Reescrever + security cleanup |
| `docs/frontend-omnichannel.md` | REWRITE | Reescrever completamente |
| `docs/wa-api.md` | REWRITE | Reescrever como visão de integração |
| `docs/n8n-workflows.md` | REWRITE | Reescrever com CURRENT/TARGET |
| `docs/media-pipeline.md` | PARTIAL_UPDATE | Atualizar paths e state machine |
| `docs/refoundation/GOAL.md` | CANONICAL | Preservar |
| `docs/refoundation/CONTRACTS.md` | CANONICAL | Preservar |
| `docs/refoundation/PLAN.md` | CURRENT_PLAN | Preservar |
| `docs/refoundation/BASELINE.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/FALLBACK_AUDIT.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/EVT_CATALOG.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/CHECKPOINT_ARCH.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/CHECKPOINT_DATA.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/N8N_ROUTER_SPEC.md` | HISTORICAL | Adicionar banner |
| `docs/refoundation/*.md` (restante) | HISTORICAL | Adicionar banner |
| `TASKS.md` | CURRENT_PLAN | Preservar |
| `features/open-delivery/*.md` | FEATURE_PARALLEL | Preservar (não é core) |
| `features/pedidos10-bridge/*.md` | FEATURE_PARALLEL | Preservar (não é core) |

### IDC_Dominuslabs

| Arquivo | Status | Ação |
|---------|--------|------|
| `README.md` | CANONICAL | Preservar |
| `goal.md` | CANONICAL | Preservar |

### api_whatsapp_v1.2

| Arquivo | Status | Ação |
|---------|--------|------|
| `README.md` | CANONICAL | Preservar |
| `ARCHITECTURE.md` | REWRITE | Reescrever com CURRENT/TARGET |
| `src/routes/README.md` | INVENTORY | Preservar com aviso |

---

## 8. PRÓXIMOS PASSOS

1. **Executar saneamento** reescrevendo os documentos identificados
2. **Adicionar banners** de status (CANONICAL, HISTORICAL, CURRENT_RUNTIME)
3. **Remover dados sensíveis** dos documentos públicos
4. **Criar links cruzados** entre documentos
5. **Validar consistência** com fontes canônicas

---

## 9. CRITÉRIOS DE PRONTO

- [ ] README.md não é mais template Vite
- [ ] docs/architecture.md reflete arquitetura canônica
- [ ] IDPW documentado como única M2M authority
- [ ] Whats API documentada como Resource Server
- [ ] Documentação distingue CURRENT de TARGET
- [ ] Fallback de sessão não é documentado como válido
- [ ] Documentação pública não contém IPs/ports/IDs reais
- [ ] Arquivos históricos possuem banner HISTORICAL
- [ ] Documentos canônicos possuem banner CANONICAL
