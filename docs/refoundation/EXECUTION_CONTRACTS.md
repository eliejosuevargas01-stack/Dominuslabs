# EXECUTION CONTRACTS — Primeiras 5 Tarefas

> **Status:** HISTORICAL / EXECUTION ARTIFACT
> Estes contratos foram congelados para tarefas iniciais específicas. Não são autoridade para a arquitetura atual; use `GOAL.md`, `CONTRACTS.md` e `PLAN.md`.

> Congelado em: 2026-09-24
> Escopo: ARCH-000, ARCH-001, ARCH-002, DATA-001, DATA-002
> Estes contratos são IMUTÁVEIS durante a execução destas 5 tarefas.
> Nenhum worker pode alterar estes contratos. Divergência = BLOCKED + retornar ao Orchestrator.

---

## CT-001 — Startup Validation Contract (ARCH-002)

### O que o backend Dominus deve fazer no startup

```python
# app/core/startup_validator.py (NOVO ARQUIVO)

class StartupValidationError(Exception):
    """Raised when a required configuration is absent or invalid."""
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"Startup validation failed: {len(errors)} error(s)")

def validate_startup_config(settings) -> None:
    """
    Validates all required environment variables.
    Raises StartupValidationError with a list of ALL errors found.
    Called BEFORE uvicorn starts accepting requests.
    """
    ...
```

### Variáveis classificadas

| Variável | Classificação | Comportamento se ausente |
|----------|--------------|--------------------------|
| `JWT_SECRET` | REQUIRED | StartupValidationError, exit 1 |
| `DATABASE_URL` | REQUIRED_IN_PROD | Erro se `ENVIRONMENT=production`; SQLite OK em dev |
| `ADMIN_PASSWORD` | REQUIRED | StartupValidationError, exit 1 |
| `N8N_WEBHOOK_SECRET` | REQUIRED | StartupValidationError, exit 1 |
| `ENCRYPTION_MASTER_KEY` | REQUIRED | StartupValidationError, exit 1 |
| `DOMINUS_PRIVATE_KEY` | REQUIRED | StartupValidationError, exit 1 |
| `IDPW_PUBLIC_KEY` | REQUIRED | StartupValidationError, exit 1 |
| `IDENTITY_WORKER_URL` | REQUIRED | StartupValidationError, exit 1 |
| `WHATSAPP_API_URL` | REQUIRED | StartupValidationError, exit 1 |
| `ADMIN_USERNAME` | HAS_SAFE_DEFAULT | Pode manter `"admin"` — documentado em .env.example |
| `UPLOAD_DIR` | HAS_SAFE_DEFAULT | Deriva do filesystem, não é secret |
| `ENVIRONMENT` | HAS_SAFE_DEFAULT | `"development"` se ausente |
| `N8N_TIMESTAMP_TOLERANCE_SECONDS` | HAS_SAFE_DEFAULT | `300` — numérico, não sensível |
| `WHATSAPP_PUBLIC_URL` | REQUIRED | StartupValidationError, exit 1 |
| `WEBHOOK_SECRET` | DEPRECATED_ALIAS | Migrar para N8N_WEBHOOK_SECRET, logar warning |

### Comportamento de erro obrigatório

```json
// stdout quando falha:
{
  "error": "STARTUP_VALIDATION_FAILED",
  "missing": ["JWT_SECRET", "ENCRYPTION_MASTER_KEY"],
  "empty": ["DOMINUS_PRIVATE_KEY"],
  "invalid": [],
  "action": "Set the missing environment variables and restart."
}
// exit code: 1
// NÃO inicia o servidor
```

### O que NÃO muda nesta task
- Nenhum endpoint existente é alterado
- Nenhum modelo de banco é alterado
- `config.py` recebe apenas: remoção de defaults sensíveis + import do validator
- `main.py` recebe apenas: chamada `validate_startup_config(settings)` antes de `uvicorn.run`

---

## CT-002 — Dashboard Metrics Contract (DATA-001 + DATA-002)

### Endpoint existente (NÃO criar novo)

```
GET /api/v1/analytics/orders?period=today|7d|30d
Authorization: Bearer <human_jwt>
```

Se o endpoint não existir ainda, o worker backend deve criá-lo nesta task:

```
Response 200:
{
  "period": {
    "from": "2026-09-24T00:00:00-03:00",
    "to":   "2026-09-24T23:59:59-03:00",
    "timezone": "America/Sao_Paulo",
    "label": "today"
  },
  "orders": {
    "count": 0,
    "revenue_cents": 0,
    "average_ticket_cents": null,
    "by_status": {
      "new": 0, "preparing": 0, "ready": 0, "delivering": 0,
      "completed": 0, "cancelled": 0
    }
  },
  "attendance": {
    "by_ia": null,
    "by_human": null,
    "pct_ia": null
  }
}

Response 401: { "detail": "Not authenticated" }
```

**Regra**: `attendance.*` = null quando não há dados reais calculáveis.
NUNCA retornar `14`, `2`, `88` ou qualquer número hardcoded.

### Frontend — DashboardOperationalView.tsx

```typescript
// CONTRATO DE ESTADO — imutável nesta task

// ANTES (proibido):
const activeSet = todayList.length > 0 ? todayList : rawList;
atendimentosIa: iaCount || 14
atendimentosHumanos: humanCount || 2
porcentagemIa: pctIa > 0 ? pctIa : 88

// DEPOIS (obrigatório):
// 1. todayList é SEMPRE a lista filtrada pela data de hoje. Nunca usar rawList como fallback.
// 2. Sem dados de IA → exibir "—" ou 0, nunca número inventado.
// 3. Período selecionado (today|7d|30d) altera a query ao backend, não apenas o filtro local.

interface DashboardMetrics {
  ordersToday: number;          // real, pode ser 0
  revenueToday: number;         // real, pode ser 0
  averageTicket: number | null; // null quando count = 0
  attendanceIA: number | null;  // null quando não calculável
  attendanceHuman: number | null;
  pctIA: number | null;
  loading: boolean;
  error: string | null;         // visível na UI, não só console
}
```

### Comportamento de exibição

```
Hoje sem pedidos:
  Pedidos Hoje: 0
  Faturamento Hoje: R$ 0,00
  Ticket Médio: —

Sem dados de IA:
  Atendimentos IA: —
  % IA: —

Erro de fetch:
  Exibir mensagem de erro na área do card
  Botão "Tentar novamente"
```

---

## CT-003 — Fallback Audit Report Contract (ARCH-001)

### Formato obrigatório do relatório

Arquivo: `docs/refoundation/FALLBACK_AUDIT.md`

```markdown
## [CLASSIFICAÇÃO] — arquivo.ext:linha

**Código:**
```lang
<código exato>
```

**Classificação**: SAFE_UI_DEFAULT | SAFE_FORMATTING_DEFAULT | RETRY | DANGEROUS_FALLBACK | SECURITY_FALLBACK | DATA_INTEGRITY_FALLBACK | SESSION_FALLBACK | CONFIG_FALLBACK | LEGACY_COMPATIBILITY

**Risco**: Descrição do que acontece se o fallback for acionado em produção.

**Ação recomendada**: Remover | Manter | Substituir por fail-closed | Documentar como safe
```

### Escopo do audit (somente leitura, zero edição de código)

| Repo | Diretórios a auditar |
|------|---------------------|
| dominuslabs | `project-hub/backend/app/` |
| api-whatsapp-service | `src/` |
| idc-dominuslabs | `src/` |

### Padrões a buscar

```
os.getenv(..., "valor")        → CONFIG_FALLBACK ou SECURITY_FALLBACK
process.env.X || "valor"       → CONFIG_FALLBACK ou SECURITY_FALLBACK
|| 14 / || 88 / || 2          → DATA_INTEGRITY_FALLBACK
|| availableSessions[0]        → SESSION_FALLBACK
catch vazio / except: pass     → DANGEROUS_FALLBACK
|| [] / || {} / || ""          → SAFE_UI_DEFAULT (avaliar contexto)
|| 0 / || null                 → SAFE_FORMATTING_DEFAULT (avaliar contexto)
```

---

## CT-004 — Baseline Document Contract (ARCH-000)

### Arquivo: `docs/refoundation/BASELINE.md`

Seções obrigatórias:

1. **Commit SHAs** — 3 repos com data e branch
2. **Workflows n8n** — ID, nome, status ativo/inativo
3. **Variáveis de ambiente necessárias** — nomes apenas, sem valores
4. **Endpoints em uso** — método + path + descrição
5. **Eventos emitidos/consumidos** — WA API → n8n → Dominus
6. **Suites de teste** — resultado real executado nesta data
7. **16 problemas conhecidos** — lista do PLAN § ARCH-000 item 9
8. **Screenshots/estado visual** — descrição textual (não screenshots nesta task)

---

## Regras de Concorrência

| Par de tasks | Mesmo arquivo? | Ação |
|-------------|---------------|------|
| ARCH-000 + ARCH-001 | Não | Paralelo OK |
| ARCH-000 + ARCH-002 | Não | Paralelo OK |
| ARCH-001 + ARCH-002 | Não | Paralelo OK (audit é read-only) |
| DATA-001 + DATA-002 | SIM — `DashboardOperationalView.tsx` | **SEQUENCIAL**: DATA-001 primeiro, DATA-002 depois |
| ARCH-002 + DATA-001 | Não | Paralelo OK |

---

## Definição de Pronto por Task

| Task | Pronto quando |
|------|--------------|
| ARCH-000 | `BASELINE.md` existe, commit feito, sem valores sensíveis |
| ARCH-001 | `FALLBACK_AUDIT.md` existe com todas as ocorrências classificadas |
| ARCH-002 | Backend recusa startup sem `JWT_SECRET`; testes passam; exit code ≠ 0 confirmado |
| DATA-001 | `Pedidos Hoje = 0` quando sem pedidos; sem fallback para `rawList`; teste passa |
| DATA-002 | Métricas IA exibem `—` quando null; sem hardcode `14/2/88`; teste passa |
