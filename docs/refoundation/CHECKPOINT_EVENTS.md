# CHECKPOINT — FASE 3: Contrato de Eventos

## EVT-001 — Catálogo de Eventos

| Campo | Valor |
|-------|-------|
| TASK | EVT-001 |
| PARENT PLAN | Catalogar eventos atuais |
| FILES | `docs/refoundation/EVT_CATALOG.md` |
| BEHAVIOR IMPLEMENTED | Mapeamento de todos os endpoints SSE e webhook do Dominus, WA API, n8n |
| TESTS | N/A (documentação) |
| LEGACY CONSUMERS | Identificados: 7 termos legacy |
| COMMIT | `35dadc62` |
| REMOTE SHA | `11d03cdf` (pendente push) |
| RISKS REMAINING | Nenhum |

---

## EVT-002 — Schema SystemEvent

| Campo | Valor |
|-------|-------|
| TASK | EVT-002 |
| PARENT PLAN | Schema SystemEvent |
| FILES | `app/events/schemas.py`, `app/events/__init__.py` |
| BEHAVIOR IMPLEMENTED | Schema Pydantic com validação de campos obrigatórios |
| TESTS | N/A (coberto por EVT-003) |
| LEGACY CONSUMERS | N/A |
| COMMIT | `11d03cdf` |
| REMOTE SHA | `11d03cdf` |
| RISKS REMAINING | Nenhum |

---

## EVT-003 — Tipos Canônicos

| Campo | Valor |
|-------|-------|
| TASK | EVT-003 |
| PARENT PLAN | Tipos canônicos |
| FILES | `app/events/types.py`, `app/events/registry.py`, `app/events/schemas.py`, `tests/test_events.py` |
| BEHAVIOR IMPLEMENTED | SystemEventType enum (13 tipos), version=Literal[1], validação UUID, timezone-aware, extra=forbid |
| TESTS | 22/22 passando |
| LEGACY CONSUMERS | 7 termos documentados em EVT_LEGACY_AUDIT.md |
| COMMIT | `3e13da8a` |
| REMOTE SHA | `11d03cdf` (pendente push) |
| RISKS REMAINING | Nenhum |

---

## EVT-004 — Event Ingress

| Campo | Valor |
|-------|-------|
| TASK | EVT-004 |
| PARENT PLAN | Event Ingress único |
| FILES | `app/api/endpoints/events.py` |
| BEHAVIOR IMPLEMENTED | POST /api/v1/webhooks/events com validação Pydantic, verificação de metadados, routing |
| TESTS | 38/38 passando (integrado com EVT-003/006) |
| LEGACY CONSUMERS | Endpoint `/webhooks/events/test` REMOVIDO |
| COMMIT | `0ac92ee0` + correção |
| REMOTE SHA | `11d03cdf` (pendente push) |
| RISKS REMAINING | Autenticação/signature verification ainda não implementada (próxima iteração) |

---

## EVT-005 — Event Router

| Campo | Valor |
|-------|-------|
| TASK | EVT-005 |
| PARENT PLAN | Event Router |
| FILES | `app/events/router.py` |
| BEHAVIOR IMPLEMENTED | EventRouter com handlers registrados, SEM fallback handler (UNHANDLED_EVENT_TYPE) |
| TESTS | 38/38 passando |
| LEGACY CONSUMERS | Fallback handler REMOVIDO |
| COMMIT | `953a19f4` + correção |
| REMOTE SHA | `11d03cdf` (pendente push) |
| RISKS REMAINING | Handlers ainda são placeholders (lógica de negócio pendente) |

---

## EVT-006 — Regra Fundamental de Mensagem

| Campo | Valor |
|-------|-------|
| TASK | EVT-006 |
| PARENT PLAN | Regra fundamental de mensagem |
| FILES | `app/events/rules.py`, `tests/test_message_rules.py` |
| BEHAVIOR IMPLEMENTED | MessageEventHandler com semântica estrita: created (cria+unread+realtime+notificação), status.updated (apenas atualiza), reaction.updated (apenas reação) |
| TESTS | 16/16 passando |
| LEGACY CONSUMERS | N/A |
| COMMIT | `fbcc6c5a` + correção |
| REMOTE SHA | `11d03cdf` (pendente push) |
| RISKS REMAINING | MessageEventHandler não integrado ao router (aguardando repositório real) |

---

## EVT-007 — n8n como Router

| Campo | Valor |
|-------|-------|
| TASK | EVT-007 |
| PARENT PLAN | n8n como router |
| FILES | `docs/refoundation/N8N_ROUTER_SPEC.md` |
| BEHAVIOR IMPLEMENTED | Documentação de migração, mapeamento WA API → SystemEvent, configuração n8n |
| TESTS | N/A (documentação) |
| LEGACY CONSUMERS | Workflows n8n ainda não migrados |
| COMMIT | `79dad4c2` |
| REMOTE SHA | `11d03cdf` (pendente push) |
| RISKS REMAINING | **Workflows n8n reais ainda não modificados** — requer acesso ao n8n MCP/API |

---

## EVT-008 — Deprecar Endpoints Antigos

| Campo | Valor |
|-------|-------|
| TASK | EVT-008 |
| PARENT PLAN | Deprecar endpoints antigos |
| FILES | `app/api/endpoints/webhooks.py`, `docs/refoundation/EVT_DEPRECATION.md` |
| BEHAVIOR IMPLEMENTED | 6 endpoints marcados como deprecated=True |
| TESTS | N/A |
| LEGACY CONSUMERS | 6 endpoints deprecados |
| COMMIT | `120decb6` |
| REMOTE SHA | `11d03cdf` (pendente push) |
| RISKS REMAINING | **Endpoints ainda não removidos** — requer migração de consumidores (EVT-007) |

---

## Resumo

| Task | Status | Bloqueio |
|------|--------|----------|
| EVT-001 | ✅ DONE | — |
| EVT-002 | ✅ DONE | — |
| EVT-003 | ✅ DONE | — |
| EVT-004 | ✅ DONE | — |
| EVT-005 | ✅ DONE | — |
| EVT-006 | ✅ DONE | — |
| EVT-007 | ⚠️ PARCIAL | Workflows n8n não migrados |
| EVT-008 | ⚠️ PARCIAL | Endpoints não removidos |

## Próximos Passos

1. **Push** da branch `refactor/dominus-refoundation`
2. **EVT-007**: Migrar workflows n8n reais (requer n8n MCP/API)
3. **EVT-008**: Remover endpoints após migração de consumidores
4. **Fase 4**: MEDIA (após conclusão de EVT-007/008)
