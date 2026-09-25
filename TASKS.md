# DominusLabs — Refoundation Task Backlog

> **Status:** CANONICAL — Execution Backlog  
> **Master Plan:** `docs/refoundation/PLAN.md`  
> **Atualizado para o estado do branch `refactor/dominus-refoundation`.**

## Legenda

- ✅ Concluído com evidência no branch
- 🚧 Em progresso
- ⬜ Pendente
- 🔴 Crítico / bloqueante
- 🟡 Importante
- 🟢 Melhoria

# FASE 0 — BASELINE

## ✅ ARCH-000 — Congelar estado atual
🔴

Evidência: `docs/refoundation/BASELINE.md`.

# FASE 1 — FALLBACKS / FAIL-CLOSED

## ✅ ARCH-001 — Inventário de fallbacks
🔴  
Evidência: `docs/refoundation/FALLBACK_AUDIT.md`.

## ✅ ARCH-002 — Configuração obrigatória
🔴

## ✅ ARCH-003 — Remover defaults sensíveis
🔴

## ✅ ARCH-004 — Auditoria do .env
🔴

Evidência consolidada: `docs/refoundation/CHECKPOINT_ARCH.md`.

# FASE 2 — INTEGRIDADE DOS DADOS

## ✅ DATA-001 — Corrigir Pedidos Hoje
🟡

## ✅ DATA-002 — Remover métricas inventadas
🟡

## ✅ DATA-003 — Períodos reais + timezone do tenant
🟡

## ✅ DATA-004 — Pedidos do período respeitam filtro
🟡

Evidência: `docs/refoundation/CHECKPOINT_DATA.md` e commits DATA correspondentes.

# FASE 3 — EVENT CONTRACT

## ✅ EVT-001 — Catalogar eventos atuais
🔴  
Evidência: `EVT_CATALOG.md`.

## ✅ EVT-002 — Schema SystemEvent
🔴

## ✅ EVT-003 — Tipos canônicos
🔴

## ✅ EVT-004 — Event Ingress
🔴

## ✅ EVT-005 — Event Router
🔴

## ✅ EVT-006 — Regra de status de mensagem
🔴

## ✅ EVT-007 — n8n router specification
🟡

## ✅ EVT-008 — Deprecação/consumer audit dos endpoints antigos
🟡

Evidência: commits EVT do branch e documentos `CHECKPOINT_EVENTS.md`, `N8N_ROUTER_SPEC.md`, `EVT_DEPRECATION.md`.

> Nota: “concluído no branch” não significa que todos os workflows externos já foram promovidos/deployados em produção. Documentação CURRENT/TARGET deve preservar essa distinção.

# FASE 4 — MÍDIA

## ⬜ MEDIA-001 — Extrair/consolidar domínio de mídia na Whats API
🔴

## ⬜ MEDIA-002 — State machine pending/downloading/ready/failed
🔴

## ⬜ MEDIA-003 — Storage `/app/data/media/{tenant}/{session}`
🔴

## ⬜ MEDIA-004 — GET somente de mídia persistida
🔴

## ⬜ MEDIA-005 — Retry explícito e observável
🟡

## ⬜ MEDIA-006 — media.processing/ready/failed
🟡

# FASE 5 — PAGINAÇÃO

## ⬜ PAG-001 — Cursor pagination de conversas
🟡

## ⬜ PAG-002 — Cursor pagination de mensagens
🟡

## ⬜ PAG-003 — Dedupe e scroll anchor
🟡

# FASE 6 — REALTIME GLOBAL

## ⬜ RT-001 — RealtimeProvider global
🔴

## ⬜ RT-002 — Router/dedupe frontend
🔴

## ⬜ RT-003 — Unificar infraestrutura realtime de WhatsApp e pedidos
🟡

# FASE 7 — NOTIFICAÇÕES

## ⬜ NOTIF-001 — Sound Engine
🔴

## ⬜ NOTIF-002 — Browser Notification API
🟡

## ⬜ NOTIF-003 — Negative notification rules
🔴

# FASE 8 — OMNICHANNEL

## ⬜ OMN-001 — Decompor OmnichannelView
🔴

## ⬜ OMN-002 — Seleção determinística de sessão
🔴

## ⬜ OMN-003 — ConversationAvatar autenticado/lazy/cache
🟡

## ⬜ OMN-004 — Media renderers específicos
🟡

## ⬜ OMN-005 — MediaViewer
🟡

## ⬜ OMN-006 — Estados loading/empty/error/disconnected
🟡

# FASE 9 — ERROR UX

## ⬜ ERR-001 — AppError
🟡

## ⬜ ERR-002 — Toast/inline/banner/blocking rules
🟡

## ⬜ ERR-003 — Eliminar catches silenciosos relevantes
🟡

# FASE 10 — APP SHELL

## ⬜ SHELL-001 — Navegação tenant
🟡

## ⬜ SHELL-002 — Linguagem do produto
🟡

# FASE 11 — MOBILE

## ⬜ MOBILE-001 — Bottom navigation
🔴

## ⬜ MOBILE-002 — Omnichannel como telas lista/chat
🔴

## ⬜ MOBILE-003 — Zero overflow/overlap
🔴

# FASE 12 — MINHA EMPRESA

## ⬜ EMP-001 — Reestruturar Company Settings
🟡

## ⬜ EMP-002 — ScrollableTabs desktop + navegação mobile
🟡

# FASE 13 — FUNCIONÁRIO DIGITAL

## ⬜ FD-001 — Conceito de Funcionário Digital
🟡

## ⬜ FD-002 — Métricas de trabalho real
🟡

## ⬜ FD-003 — Configuração operacional
🟡

# FASE 14 — ORDER MANAGER

## ⬜ OM-001 — Board operacional por estado
🟡

## ⬜ OM-002 — Cards operacionais compactos
🟡

## ⬜ OM-003 — Métricas operacionais
🟡

# FASE 15 — DASHBOARD

## ⬜ DASH-001 — Visão operacional usando dados reais
🟡

# FASE 16 — PERFIL

## ⬜ PROFILE-001 — Meu Perfil separado de Minha Empresa
🟢

## ⬜ PROFILE-002 — Preferências suportadas
🟢

# FASE 17 — BACKEND DOMINUS

## ⬜ DEC-BE-001 — Decompor webhooks.py
🟡

## ⬜ DEC-BE-002 — Decompor n8n_service.py
🟡

## ⬜ DEC-BE-003 — Correlation IDs
🟡

# FASE 18 — WHATS API

## ⬜ DEC-WA-001 — Decompor session.manager.js
🟡

## ⬜ DEC-WA-002 — Cleanup legacy com consumer proof
🟡

# FASE 19 — DESIGN SYSTEM / SKILL

## ⬜ SKILL-001 — dominus-frontend SKILL.md
🟢

# FASE 20 — PERFORMANCE

## ⬜ PERF-OPT-001 — Conversas/mensagens
🟢

## ⬜ PERF-OPT-002 — Avatar/mídia
🟢

# FASE 21 — PWA

## ⬜ PWA-001 — Manifest/installability
🟢

## ⬜ PWA-002 — Service Worker + Web Push
🟢

# FASE 22 — TESTES DE CONTRATO

## ⬜ TEST-001 — Events
🔴

## ⬜ TEST-002 — Media
🔴

## ⬜ TEST-003 — Pagination
🟡

## ⬜ TEST-004 — Notification rules
🔴

# FASE 23 — E2E / REGRESSÃO

## ⬜ E2E-001 — Playwright nos breakpoints definidos
🔴

# FASE 24 — ACESSIBILIDADE

## ⬜ A11Y-001 — Keyboard/focus/labels/touch targets
🟡

# FASE 25 — OBSERVABILIDADE

## ⬜ OBS-001 — Event/request/media correlation
🟡

## ⬜ OBS-002 — Sanitização de logs
🔴

# FASE 26 — LEGACY CLEANUP

## ⬜ LEGACY-001 — Reauditar compatibilidade residual
🟡

## ⬜ LEGACY-002 — Remover somente após consumer proof
🔴

# FASE 27 — DOCUMENTAÇÃO FINAL

## 🚧 DOC-001 — Saneamento documental
🟡

Escopo atual: alinhar documentos canônicos, remover contradições e sanitizar artefatos históricos.

## ⬜ DOC-002 — Auditoria documental final pós-Refoundation
🟢

# Dependências principais

```text
ARCH → DATA → EVT → MEDIA → PAG → RT → NOTIF → OMN
                                      ↓
                                    ERROR UX
                                      ↓
                                  SHELL/MOBILE
                                      ↓
                         PRODUCT AREAS / DECOMPOSITION
                                      ↓
                         PERFORMANCE / PWA / A11Y / OBS
                                      ↓
                              E2E / LEGACY / DOCS
```

# Regra para agentes

Não iniciar task visual conveniente se uma dependência estrutural anterior estiver pendente.

Exemplos:

- não implementar PWA antes de realtime global/notificações;
- não criar MediaViewer dependendo de contrato de mídia temporário;
- não redesenhar Omnichannel preservando fallback de sessão;
- não remover endpoint legado antes do consumer proof.
