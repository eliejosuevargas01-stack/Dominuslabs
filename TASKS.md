# DominusLabs — Refoundation Task Backlog

> Gerado: 23/09/2026 — Dominus Product & Architecture Refoundation
> Substitui backlog anterior. Documentos: docs/refoundation/GOAL.md, PLAN.md, CONTRACTS.md
> Nenhuma task será executada sem visto positivo do usuário.

---

## Legenda

- 🔴 Crítico / Bloqueante
- 🟡 Importante
- 🟢 Melhoria
- ✅ Concluído
- 🚧 Em progresso
- ⬜ Pendente

---

# FASE 0 — INVENTÁRIO E BASELINE

## 🚧 ARCH-000 — Congelar estado atual
🔴 Crítico | Sequencial: primeira tarefa

**Objetivo**: Documentar baseline antes de qualquer alteração estrutural.

**Repositórios**: Dominuslabs, IDC_Dominuslabs, api-whatsapp-service

**Subtarefas**:
1. Registrar commit SHA dos 3 repos
2. Listar workflows n8n envolvidos (IDs e nomes)
3. Registrar variáveis de ambiente necessárias (sem valores)
4. Registrar endpoints atualmente utilizados (backend + WA API)
5. Registrar eventos emitidos (WA API → n8n → Dominus)
6. Registrar eventos consumidos (SSE, webhooks)
7. Executar suites existentes e registrar resultados
8. Registrar problemas já reproduzidos (16 itens do baseline)

**Aceite**: Baseline documentado em `docs/refoundation/BASELINE.md`.

---

# FASE 1 — AUDITORIA DE FALLBACKS E FAIL-CLOSED

## ⬜ ARCH-001 — Inventário de fallbacks
🔴 Crítico | Sequencial: após ARCH-000

**Objetivo**: Auditar os 3 repos + n8n buscando padrões de fallback.

**Padrões a buscar**: `||`, `??`, ternários, `DEFAULT_`, `default=`, `os.getenv(..., "valor")`, `process.env.X || "valor"`, catch vazio, `except: pass`, mock value, hardcoded tenant/credential/endpoint.

**Classificação**: SAFE_UI_DEFAULT, SAFE_FORMATTING_DEFAULT, RETRY, DANGEROUS_FALLBACK, SECURITY_FALLBACK, DATA_INTEGRITY_FALLBACK, SESSION_FALLBACK, CONFIG_FALLBACK, LEGACY_COMPATIBILITY.

**Aceite**: Relatório classificado antes de remoção.

## ⬜ ARCH-002 — Configuração obrigatória
🔴 Crítico | Paralelo com: ARCH-001

**Objetivo**: Criar schemas de environment por aplicação. Startup falha sem config necessária.

## ⬜ ARCH-003 — Remover defaults sensíveis
🔴 Crítico | Sequencial: após ARCH-001

**Objetivo**: Eliminar defaults como admin123, secrets previsíveis, URLs reais em Docker Compose/source.

## ⬜ ARCH-004 — Auditoria do .env versionado
🔴 Crítico | Paralelo com: ARCH-003

**Objetivo**: Verificar se .env no Git contém/conteve credenciais. Rotacionar, remover do tracking.

**Aceite Fase 1**: Nenhum secret tem fallback funcional; startup falha sem config; inventário produzido.

---

# FASE 2 — CORREÇÃO DA INTEGRIDADE DOS DADOS

## ⬜ DATA-001 — Corrigir "Pedidos Hoje"
🟡 Importante | Sequencial: após Fase 1

**Arquivo**: `src/pages/DashboardOperationalView.tsx`, backend analytics endpoints

**Problema**: `todayList.length > 0 ? todayList : rawList` — histórico como fallback.

**Aceite**: Hoje sem pedidos → 0.

## ⬜ DATA-002 — Remover métricas inventadas
🟡 Importante | Paralelo com: DATA-001

**Problema**: `iaCount || 14`, `pctIa > 0 ? pctIa : 88`

**Aceite**: Sem dado → "—" ou "Dados ainda não disponíveis" ou 0.

## ⬜ DATA-003 — Período real de métricas
🟡 Importante | Sequencial: após DATA-001

**Objetivo**: Backend analítico `GET /analytics/overview?period=today|7d|30d` com timezone do tenant.

## ⬜ DATA-004 — Pedidos recentes respeitam filtro
🟡 Importante | Sequencial: após DATA-003

**Aceite**: Lista reflete período selecionado ou declara independência clara.

---

# FASE 3 — CONTRATO ÚNICO DE EVENTOS

## ⬜ EVT-001 — Catalogar eventos atuais
🔴 Crítico | Sequencial: após Fase 2

**Objetivo**: Mapear eventos em WA API, n8n Switch/IFs, Dominus endpoints. Identificar duplicações semânticas.

## ⬜ EVT-002 — Schema SystemEvent
🔴 Crítico | Sequencial: após EVT-001

**Objetivo**: Contrato versionado com event_id, type, tenant_id, session_id, occurred_at, payload.

## ⬜ EVT-003 — Tipos canônicos
🔴 Crítico | Paralelo com: EVT-002

**Tipos**: message.created, message.status.updated, message.reaction.updated, conversation.updated, media.*, session.*, order.*

## ⬜ EVT-004 — Event Ingress único
🔴 Crítico | Sequencial: após EVT-002 + EVT-003

**Objetivo**: `POST /webhooks/events` — ponto único de entrada com signature validation, idempotency, routing.

## ⬜ EVT-005 — Event Router
🟡 Importante | Sequencial: após EVT-004

**Objetivo**: `app/events/` com schemas, registry, router, handlers por tipo.

## ⬜ EVT-006 — Regra fundamental de mensagem
🔴 Crítico | Paralelo com: EVT-005

**Regra**: message.status.updated NUNCA incrementa unread, cria mensagem, toca som ou emite notification.

## ⬜ EVT-007 — n8n como router
🟡 Importante | Sequencial: após EVT-004

**Objetivo**: Switch n8n usa `type` diretamente, não reconstrói tipo.

## ⬜ EVT-008 — Deprecar endpoints antigos
🟡 Importante | Sequencial: após migração completa de EVT-004..007

---

# FASE 4 — MÍDIA

## ⬜ MEDIA-001 — Media state machine na WA API
🟡 Importante | Sequencial: após Fase 3

**Objetivo**: pending → downloading → ready → failed. Persistência em `/app/data/media/{tenant}/{session}/`.

## ⬜ MEDIA-002 — Frontend usa URLs internas
🟡 Importante | Sequencial: após MEDIA-001

**Objetivo**: Frontend nunca depende de pps.whatsapp.net/fbcdn.net.

---

# FASE 5 — PAGINAÇÃO

## ⬜ PAG-001 — Cursor pagination conversas
🟡 Importante | Sequencial: após Fase 4

## ⬜ PAG-002 — Cursor pagination mensagens
🟡 Importante | Paralelo com: PAG-001

---

# FASE 6 — REALTIME GLOBAL

## ⬜ RT-001 — RealtimeProvider global
🔴 Crítico | Sequencial: após Fase 5

**Objetivo**: SSE/realtime montado na app autenticada, não dentro do OmnichannelView.

## ⬜ RT-002 — Sound Engine + Notification Engine
🟡 Importante | Sequencial: após RT-001

**Regra**: Som somente para message.created AND incoming AND não processado.

---

# FASE 7 — OMNICHANNEL

## ⬜ OMN-001 — Decomposição OmnichannelView.tsx (2725 linhas)
🔴 Crítico | Sequencial: após Fase 6

## ⬜ OMN-002 — Media renderers específicos
🟡 Importante | Paralelo com: OMN-001

## ⬜ OMN-003 — MediaViewer global (image zoom/pan, video fullscreen, sticker)
🟡 Importante | Sequencial: após OMN-002

## ⬜ OMN-004 — ConversationAvatar unificado
🟡 Importante | Paralelo com: OMN-001

---

# FASE 8 — ERROR UX

## ⬜ ERR-001 — Contrato AppError
🟡 Importante | Sequencial: após Fase 7

## ⬜ ERR-002 — Eliminar .catch(() => {})
🟡 Importante | Paralelo com: ERR-001

---

# FASE 9 — APP SHELL + MOBILE

## ⬜ SHELL-001 — Mobile shell com bottom navigation
🟡 Importante | Sequencial: após Fase 8

## ⬜ SHELL-002 — Desktop shell + menu renomeado
🟡 Importante | Paralelo com: SHELL-001

## ⬜ SHELL-003 — Browser Notifications
🟡 Importante | Sequencial: após RT-002

---

# FASE 10 — ORDER MANAGER + DASHBOARD + MINHA EMPRESA

## ⬜ OM-001 — OrderManagerView.tsx refactor (1353 linhas)
🟡 Importante | Sequencial: após Fase 9

## ⬜ DASH-001 — Dashboard métricas reais
🟡 Importante | Paralelo com: OM-001

## ⬜ EMP-001 — CompanySettingsView.tsx refactor (1297 linhas) → "Minha Empresa"
🟡 Importante | Paralelo com: OM-001

---

# FASE 11 — FUNCIONÁRIO DIGITAL + PERFIL

## ⬜ FD-001 — Conceito "Funcionário Digital" substitui IA
🟢 Melhoria | Sequencial: após Fase 10

## ⬜ PERF-001 — Página "Meu Perfil"
🟢 Melhoria | Paralelo com: FD-001

---

# FASE 12 — DECOMPOSIÇÃO FINAL

## ⬜ DEC-001 — session.manager.js decomposição (2347 linhas)
🟡 Importante | Sequencial: após Fase 11

## ⬜ DEC-002 — webhooks.py decomposição (1178 linhas)
🟡 Importante | Paralelo com: DEC-001

## ⬜ DEC-003 — n8n_service.py decomposição (1524 linhas)
🟡 Importante | Paralelo com: DEC-001

---

# FASE 13 — E2E / REGRESSÃO

## ⬜ E2E-001 — Suite Playwright completa
🔴 Crítico | Sequencial: após Fase 12

**Breakpoints**: 375x812, 390x844, 414x896, 768x1024, 1366x768, 1440x900, 1920x1080

---

# FASE 14 — DESIGN SYSTEM SKILL

## ⬜ SKILL-001 — Criar dominus-frontend SKILL.md
🟢 Melhoria | Paralelo com: qualquer fase

---

## Grafo de Dependências

```
ARCH-000
  ↓
ARCH-001 ←→ ARCH-002
  ↓            ↓
ARCH-003 ←→ ARCH-004
  ↓
DATA-001 ←→ DATA-002
  ↓
DATA-003 → DATA-004
  ↓
EVT-001 → EVT-002 ←→ EVT-003
                ↓
           EVT-004 → EVT-005
                ↓        ↓
           EVT-006    EVT-007
                ↓
           EVT-008
  ↓
MEDIA-001 → MEDIA-002
  ↓
PAG-001 ←→ PAG-002
  ↓
RT-001 → RT-002
  ↓
OMN-001 ←→ OMN-002 ←→ OMN-004
              ↓
           OMN-003
  ↓
ERR-001 ←→ ERR-002
  ↓
SHELL-001 ←→ SHELL-002
  ↓
OM-001 ←→ DASH-001 ←→ EMP-001
  ↓
FD-001 ←→ PERF-001
  ↓
DEC-001 ←→ DEC-002 ←→ DEC-003
  ↓
E2E-001
```

---

## Referências Rápidas

### Containers
- **DominusLabs backend**: `sjrweu7rw8e3nywm5stef2ri-*` (app 38)
- **WA API**: `hkossco0sggwwwss0cwk4w0s-*` (app 32)
- **Coolify DB**: `coolify-db`
- **VPS**: `ssh -p 2222 root@72.60.247.157`

### Repositórios
- Frontend + Backend: `/home/eliezer/Escritorio/dominuslabs`
- WA API: `/home/eliezer/Escritorio/api-whatsapp-service`
- IDC: `/home/eliezer/Escritorio/idc-dominuslabs`

### n8n
- URL: `https://myn8n.seommerce.shop`
- Dominus AI: `YqDBFFzJ1L4FRAvz`
- Dominus AI Buffer: `4ANz4lSb80pCuAT4`
- dominuslabs_respostas_leads: `SpQwyDZsOo3ozXuE`
- dominuslabs_crm: `WJ37gGiodnAJVkBN`

### Volumes WA API (bind mounts persistentes)
- `/app/sessions` — credenciais Baileys
- `/app/data` — mídia, mensagens, conversas
- `/app/keys` — chaves criptográficas

---

## Histórico de Conclusões

| Data | ID | Descrição |
|---|---|---|
| 23/09/2026 | — | Backlog refeito para Refoundation. Antigo backlog (T1-T12) absorvido nas fases macro. |
