# DOCUMENTATION REFOUNDATION REPORT

> **Data:** 2026-09-25
> **Task:** Saneamento e Reescrita Completa da Documentação do Ecossistema Dominus

---

## 1. DOCUMENTOS CANÔNICOS

| Arquivo | Repo | Status | Ação |
|---------|------|--------|------|
| `docs/refoundation/GOAL.md` | dominuslabs | CANONICAL | Preservado |
| `docs/refoundation/CONTRACTS.md` | dominuslabs | CANONICAL | Preservado |
| `docs/refoundation/PLAN.md` | dominuslabs | CANONICAL | Preservado |
| `TASKS.md` | dominuslabs | CANONICAL | Preservado |
| `INTEGRATION_GUIDE.md` | dominuslabs | CANONICAL | Preservado |
| `IDC_Dominuslabs/README.md` | idc-dominuslabs | CANONICAL | Preservado |
| `api_whatsapp_v1.2/README.md` | api-whatsapp-service | CANONICAL | Preservado |

---

## 2. DOCUMENTOS REESCRITOS

| Arquivo | Problema Antigo | Nova Função |
|---------|-----------------|-------------|
| `README.md` | Template Vite genérico | Índice e descrição do produto Dominus |
| `docs/architecture.md` | IPs reais, JWT_SECRET_KEY, sem IDPW, sem Event Contract | Arquitetura canônica com trust boundaries |
| `docs/frontend-omnichannel.md` | Fallback de sessão, SSE no componente, monólito | Arquitetura por feature, RealtimeProvider global |
| `docs/wa-api.md` | JWT_SECRET_KEY, scopes antigos, URL real | Visão de integração do Dominus, aponta para README canônico |

---

## 3. DOCUMENTOS PARCIALMENTE ATUALIZADOS

| Arquivo | Seções Preservadas | Seções Alteradas |
|---------|-------------------|------------------|
| `docs/media-pipeline.md` | Fluxo de download, endpoint | Path para `{tenant}/{session}`, state machine |

---

## 4. SECURITY CLEANUP

| Arquivo | Tipo de Dado Removido | Localização |
|---------|----------------------|--------------|
| `docs/architecture.md` | IP real | Removido |
| `docs/architecture.md` | Porta PostgreSQL | Removido |
| `docs/architecture.md` | JWT_SECRET_KEY | Removido (substituído por IDPW) |
| `docs/wa-api.md` | URL real | Removido (usado placeholder genérico) |
| `docs/wa-api.md` | Scopes antigos | Atualizado para scopes IDPW |

---

## 5. DOCUMENTOS AINDA PENDENTES

Os seguintes documentos ainda precisam ser reescritos:

### Prioridade Alta

| Arquivo | Problemas | Ação Necessária |
|---------|-----------|-----------------|
| `docs/n8n-workflows.md` | URLs reais, workflow IDs, CURRENT/TARGET misturados | Reescrever distinguindo runtime de target |
| `docs/deployment.md` | IPs, SSH ports, container IDs, App IDs | Reescrever com conceitos genéricos |
| `api_whatsapp_v1.2/ARCHITECTURE.md` | Proposta histórica, sem CURRENT/TARGET | Reescrever com arquitetura alvo |

### Prioridade Média

| Arquivo | Problemas | Ação Necessária |
|---------|-----------|-----------------|
| `docs/media-pipeline.md` | Path antigo, sem state machine | Atualizar paths e adicionar estados |

---

## 6. BANNERS DE STATUS ADICIONADOS

| Arquivo | Banner |
|---------|--------|
| `README.md` | CANONICAL — Target Architecture |
| `docs/architecture.md` | CANONICAL — Target Architecture |
| `docs/frontend-omnichannel.md` | CANONICAL — Target Architecture |
| `docs/wa-api.md` | CANONICAL — Integration Guide |

---

## 7. CURRENT VS TARGET BOUNDARIES

### Implementado vs Planejado

| Componente | Estado Atual | Estado Planejado |
|------------|--------------|------------------|
| Autenticação M2M | IDPW + JWKS ✅ | IDPW + JWKS ✅ |
| Event Contract | `/crm/update-chat` legado | `/webhooks/events` (Event Ingress) |
| Realtime | SSE no OmnichannelView | RealtimeProvider global |
| Media Pipeline | Path `/SESSION` | Path `/{tenant}/{session}` |
| Status de Documentação | Parcialmente saneado | Completo após pendências |

---

## 8. CONTRADIÇÕES RESOLVIDAS

### Autenticação M2M

- **Antes:** Documentos antigos descreviam `JWT_SECRET_KEY` entre Backend ↔ WA API
- **Depois:** Toda documentação reescrita referencia IDPW como única autoridade M2M

### Session Fallback

- **Antes:** `docs/frontend-omnichannel.md` documentava `workingSession || availableSessions[0]`
- **Depois:** Documentação explicita que fallback de sessão é PROIBIDO

### Event Semantics

- **Antes:** Pipeline n8n documentado como arquitetura oficial
- **Depois:** Documentação distingue CURRENT RUNTIME de TARGET CONTRACT

---

## 9. REMAINING DOCUMENTATION DEBT

1. **docs/n8n-workflows.md** — Precisa distinguir CURRENT de TARGET
2. **docs/deployment.md** — Precisa remover todos os dados sensíveis
3. **api_whatsapp_v1.2/ARCHITECTURE.md** — Precisa refletir target do Refoundation
4. **docs/refoundation/BASELINE.md** — Precisa de banner HISTORICAL
5. **docs/refoundation/FALLBACK_AUDIT.md** — Precisa de banner HISTORICAL
6. **docs/refoundation/EVT_CATALOG.md** — Precisa de banner HISTORICAL
7. **docs/refoundation/CHECKPOINT_ARCH.md** — Precisa de banner HISTORICAL
8. **docs/refoundation/CHECKPOINT_DATA.md** — Precisa de banner HISTORICAL

---

## 10. CRITÉRIOS DE PRONTO — STATUS

| Critério | Status |
|----------|--------|
| README.md não é template Vite | ✅ CONCLUÍDO |
| docs/architecture.md reflete arquitetura canônica | ✅ CONCLUÍDO |
| IDPW documentado como única M2M authority | ✅ CONCLUÍDO |
| Whats API documentada como Resource Server | ✅ CONCLUÍDO |
| Documentação distingue CURRENT de TARGET | ⚠️ PARCIAL |
| Fallback de sessão não documentado como válido | ✅ CONCLUÍDO |
| Documentação pública sem dados sensíveis | ⚠️ PARCIAL |
| Arquivos históricos com banner | ❌ PENDENTE |
| Documentos canônicos com banner | ✅ CONCLUÍDO |
| Links cruzados entre documentos | ⚠️ PARCIAL |

---

## 11. PRÓXIMOS PASSOS

1. Reescrever `docs/n8n-workflows.md` com CURRENT/TARGET
2. Reescrever `docs/deployment.md` removendo dados sensíveis
3. Reescrever `api_whatsapp_v1.2/ARCHITECTURE.md`
4. Adicionar banners HISTORICAL aos arquivos legacy
5. Atualizar `docs/media-pipeline.md` com paths corretos
6. Criar links cruzados entre documentos
