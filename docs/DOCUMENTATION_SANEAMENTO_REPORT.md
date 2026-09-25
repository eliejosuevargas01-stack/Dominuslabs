# DOCUMENTATION REFOUNDATION REPORT

> **Data:** 2026-09-25
> **Status:** CONCLUÍDO ✅

---

## 1. DOCUMENTOS CANÔNICOS — PRESERVADOS

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

## 2. DOCUMENTOS REESCRITOS COMPLETAMENTE

| Arquivo | Problema Antigo | Nova Função |
|---------|-----------------|-------------|
| `README.md` | Template Vite genérico | Índice e descrição do produto Dominus |
| `docs/architecture.md` | JWT_SECRET_KEY, IP real, sem IDPW, sem Event Contract | Arquitetura canônica com trust boundaries |
| `docs/frontend-omnichannel.md` | Fallback de sessão proibido, SSE no componente, monólito | Arquitetura por feature, RealtimeProvider global |
| `docs/wa-api.md` | JWT_SECRET_KEY, scopes antigos, URL real, duplicação | Visão de integração apontando para README canônico |
| `docs/n8n-workflows.md` | URLs/IDs reais, CURRENT/TARGET misturados | Diferenciação clara runtime vs target |
| `docs/deployment.md` | IPs, SSH, container IDs, App IDs, URLs operacionais | Documentação genérica, dados sensíveis removidos |
| `docs/media-pipeline.md` | Path antigo, sem state machine | State machine, path tenant-aware |
| `api_whatsapp_v1.2/ARCHITECTURE.md` | Proposta histórica de modularização | Documentação do Resource Server |

---

## 3. DOCUMENTOS HISTORICAL — BANNERS ADICIONADOS

| Arquivo | Banner Adicionado |
|---------|-------------------|
| `docs/refoundation/BASELINE.md` | HISTORICAL / AUDIT ARTIFACT |
| `docs/refoundation/FALLBACK_AUDIT.md` | HISTORICAL / AUDIT ARTIFACT |
| `docs/refoundation/EVT_CATALOG.md` | HISTORICAL / AUDIT ARTIFACT |
| `docs/refoundation/CHECKPOINT_ARCH.md` | HISTORICAL / AUDIT ARTIFACT |
| `docs/refoundation/CHECKPOINT_DATA.md` | HISTORICAL / AUDIT ARTIFACT |
| `docs/refoundation/N8N_ROUTER_SPEC.md` | HISTORICAL / AUDIT ARTIFACT |

---

## 4. SECURITY CLEANUP — REMOVIDO

| Tipo de Dado | Quantos Arquivos |
|---------------|------------------|
| IPs públicos reais | 2 arquivos |
| SSH ports/users | 1 arquivo |
| Container IDs | 1 arquivo |
| App IDs | 1 arquivo |
| URLs operacionais privadas | 3 arquivos |
| Workflow IDs | 1 arquivo |
| JWT_SECRET_KEY | 2 arquivos |

---

## 5. CONTRADIÇÕES RESOLVIDAS

### Autenticação M2M

| Antes | Depois |
|-------|--------|
| JWT_SECRET_KEY entre Backend ↔ WA API | IDPW como única autoridade M2M |

### Session Fallback

| Antes | Depois |
|-------|--------|
| `workingSession \|\| availableSessions[0]` documentado | Fallback de sessão PROIBIDO |

### Event Semantics

| Antes | Depois |
|-------|--------|
| Pipeline n8n como arquitetura oficial | Distinção CURRENT RUNTIME vs TARGET CONTRACT |

---

## 6. CURRENT VS TARGET BOUNDARIES

| Componente | Estado Atual | Estado Planejado |
|------------|--------------|------------------|
| Autenticação M2M | IDPW + JWKS ✅ | IDPW + JWKS ✅ |
| Autenticação Humana | Dominus JWT ✅ | Dominus JWT ✅ |
| Event Contract | `/crm/update-chat` legado | `/webhooks/events` (Event Ingress) |
| Realtime | SSE no OmnichannelView | RealtimeProvider global |
| Media Pipeline | Path `/SESSION` | Path `/{tenant}/{session}` |
| Deployment Docs | Dados sensíveis expostos | Genérico, runbooks privados |

---

## 7. CRITÉRIOS DE PRONTO — ESTADO FINAL

| Critério | Status |
|----------|--------|
| README.md não é template Vite | ✅ CONCLUÍDO |
| docs/architecture.md reflete arquitetura canônica | ✅ CONCLUÍDO |
| IDPW documentado como única M2M authority | ✅ CONCLUÍDO |
| Whats API documentada como Resource Server | ✅ CONCLUÍDO |
| Documentação distingue CURRENT de TARGET | ✅ CONCLUÍDO |
| Fallback de sessão não documentado como válido | ✅ CONCLUÍDO |
| Documentação pública sem dados sensíveis | ✅ CONCLUÍDO |
| Arquivos históricos com banner HISTORICAL | ✅ CONCLUÍDO |
| Documentos canônicos com banner CANONICAL | ✅ CONCLUÍDO |
| Links cruzados entre documentos | ⚠️ PARCIAL (referências básicas) |

---

## 8. COMMITS REALIZADOS

| Commit | Repo | Mensagem |
|--------|------|----------|
| `1061868f` | dominuslabs | `docs: saneamento parcial da documentação - Refoundation` |
| `5d14a47e` | dominuslabs | `docs: completar saneamento documentação - Refoundation` |
| `129a10a` | api-whatsapp-service | `docs: reescrever ARCHITECTURE.md - Refoundation` |

---

## 9. PRÓXIMOS PASSOS RECOMENDADOS

1. **Push para remoto** dos commits
2. **Implementar Event Ingress** no Dominus (`POST /webhooks/events`)
3. **Criar RealtimeProvider global** no frontend
4. **Mapear consumers** dos endpoints antigos de webhook
5. **Migrar n8n** para usar novos tipos de evento
6. **Remover JWT_SECRET_KEY** restante do código (se existir)

---

## 10. DOCUMENTAÇÃO FINAL CANÔNICA

### Arquitetura

- `README.md` — Índice do produto
- `docs/architecture.md` — Arquitetura geral
- `docs/refoundation/GOAL.md` — Visão
- `docs/refoundation/CONTRACTS.md` — Contratos
- `INTEGRATION_GUIDE.md` — Integração M2M

### Frontend

- `docs/frontend-omnichannel.md` — Omnichannel architecture
- `docs/media-pipeline.md` — Media pipeline

### Integrações

- `docs/wa-api.md` — Integração Whats API
- `docs/n8n-workflows.md` — Workflows n8n

### Histórico

- `docs/refoundation/BASELINE.md` — Baseline (HISTORICAL)
- `docs/refoundation/CHECKPOINT_*.md` — Checkpoints (HISTORICAL)

---

## Conclusão

A documentação foi saneada com sucesso. Agora existe uma **única narrativa arquitetural coerente**:
- Dominus como business control plane
- IDPW como única autoridade M2M
- Whats API como Resource Server
- n8n como event router

**Nenhuma ambiguidade permanece** sobre trust boundaries, autenticação, ou ownership de recursos.
