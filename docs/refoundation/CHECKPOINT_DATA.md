# CHECKPOINT DATA-001/002/003 — 2026-09-24

## DATA-001 — Pedidos Hoje: eliminar fallback para rawList

**PARENT PLAN:** DATA-001 (PLAN §Integridade de Dados)
**FILES:** `src/pages/DashboardOperationalView.tsx`, `src/pages/DashboardOperationalView.test.tsx`
**BEFORE:** `const activeSet = todayList.length > 0 ? todayList : rawList;` (linha 132)
**AFTER:** Componente sem fetch interno, sem rawList, sem internalOrders — depende exclusivamente de props
**TESTS:** `npx vitest run src/pages/DashboardOperationalView.test.tsx` → 4/4 pass
**SEARCH FOR OLD PATTERN:** `grep "todayList.length > 0\|rawList\|internalOrders\|internalMetrics"` → **vazio** ✅
**COMMIT:** `b6fd1cd2`
**RISKS REMAINING:** Nenhum para o escopo DATA-001. App.tsx passa props — resolvido por DATA-003.

---

## DATA-002 — Eliminar métricas hardcoded de IA/Humano

**PARENT PLAN:** DATA-002 (PLAN §Integridade de Dados)
**FILES:** `src/pages/DashboardOperationalView.tsx`, `project-hub/backend/app/api/endpoints/operational_metrics.py`
**BEFORE:** `atendimentosIa: iaCount || 14`, `atendimentosHumanos: humanCount || 2`, `porcentagemIa: pctIa > 0 ? pctIa : 88`
**AFTER:**
- Frontend: sem fallbacks hardcoded — usa `effectiveEfficiency.atendimentosIa` direto
- Backend: `atendimentos_ia = result[0] if result else 0` (nunca inventado)
- Backend: `atendimentos_humanos = max(0, pedidos_hoje - atendimentos_ia)` (nunca inventado)
**TESTS:** `npx vitest run src/pages/DashboardOperationalView.test.tsx` → 4/4 pass
**SEARCH FOR OLD PATTERN:** `grep "|| 14\||| 88\||| 2\b\|iaCount\|humanCount\|pctIa"` → **vazio** ✅
**COMMIT:** `b6fd1cd2` + `84c3d3fd`
**RISKS REMAINING:** Nenhum para o escopo DATA-002.

---

## DATA-003 — Conectar DashboardOperationalView ao backend

**PARENT PLAN:** DATA-003 (PLAN §Integridade de Dados)
**FILES:** `src/pages/DashboardOperationalView.tsx`, `src/services/api.ts`, `project-hub/backend/app/api/endpoints/operational_metrics.py`, `project-hub/backend/app/api/router.py`
**BEFORE:** `<DashboardOperationalView />` renderizado sem props — dashboard estático vazio
**AFTER:**
- `fetchOperationalDashboard(filterPeriod)` em `api.ts` com tipos TypeScript
- `useState` para `apiMetrics/apiEfficiency/apiOrders` — dados da API chegam ao render
- `useEffect` reage a `filterPeriod` — filtro funcional
- Backend: `get_periodo_range(periodo)` implementa hoje/7d/30d
- Backend: todas as queries usam `created_at >= :inicio AND created_at <= :fim`
- Backend: endpoints auxiliares com `current_user` dependency
- Skeleton loading + error handling com toast
**TESTS:** `npx vitest run src/pages/DashboardOperationalView.test.tsx` → 4/4 pass
**TYPESCRIPT:** `npx tsc --noEmit` → 0 erros
**COMMIT:** `b17411c2` + `ecd1c257` + `84c3d3fd` + `bd50b47c`
**RISKS REMAINING:**
- `calcular_tempo_atendimento` retorna strings fixas para EM_PREPARO/CONCLUIDO ("5-10 min", "15-30 min") — impreciso mas não inventado (melhoria futura)
- Eficiência IA é proxy (conta orders com items), não dado real de atendimento — comentário no código admite isso

---

## Validação Cruzada

| Critério | Evidência |
|----------|-----------|
| Hoje consulta somente hoje | `get_periodo_range("hoje")` → `inicio=hoje 00:00:00, fim=hoje 23:59:59` |
| 7 dias muda o range | `get_periodo_range("7d")` → `inicio=now-7d 00:00:00` |
| 30 dias muda o range | `get_periodo_range("30d")` → `inicio=now-30d 00:00:00` |
| Timezone | `datetime.utcnow()` — UTC, sem fallback local |
| Zero pedidos hoje retorna 0 | `pedidos_hoje = result[0] if result else 0` |
| Ticket médio sem base → 0 | `ticket_medio = float(result[0] or 0)` |
| Filtros não são só visual | `useEffect` reage a `filterPeriod`, backend usa range |
| Tabela não mistura histórico | `created_at >= :inicio AND created_at <= :fim` na query de orders |
