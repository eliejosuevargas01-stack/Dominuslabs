# DOCUMENTATION REFOUNDATION REPORT

> **Data:** 2026-09-25  
> **Status:** CONCLUÍDO — documentação alinhada e auditada  
> **Escopo desta correção:** somente documentação. Nenhum código/teste/runtime foi modificado pelos commits desta correção.

## 1. Fontes canônicas finais

### Dominuslabs

| Arquivo | Papel |
|---|---|
| `README.md` | entrada do produto e índice documental |
| `docs/architecture.md` | arquitetura global target |
| `docs/refoundation/GOAL.md` | visão e princípios |
| `docs/refoundation/CONTRACTS.md` | invariantes |
| `docs/refoundation/PLAN.md` | master implementation plan completo |
| `TASKS.md` | backlog e estado de execução |
| `INTEGRATION_GUIDE.md` | integração Dominus/IDPW/Whats API/n8n |
| `docs/wa-api.md` | integração Dominus↔Whats API |
| `docs/frontend-omnichannel.md` | arquitetura target do Omnichannel |

### IDPW

| Arquivo | Papel |
|---|---|
| `README.md` | CANONICAL runtime contract |
| `goal.md` | histórico/implemented goal; não canônico |

### Whats API

| Arquivo | Papel |
|---|---|
| `README.md` | CANONICAL runtime contract |
| `ARCHITECTURE.md` | arquitetura current/target do Resource Server |
| `goal.md` | superseded historical goal |
| `src/routes/README.md` | inventário técnico não canônico |
| `frontend/README.md` | fonte histórica desconectada |

## 2. Correções principais

### `docs/wa-api.md`

O arquivo anterior continha uma nova introdução seguida da especificação legacy antiga no mesmo documento. Foi substituído integralmente por um único contrato coerente:

```text
IDPW = M2M authority
Dominus = business/control plane
Whats API = Resource Server
Browser = sem autoridade M2M
```

Scopes antigos e descrição de assinatura local de JWT foram removidos.

### `INTEGRATION_GUIDE.md`

Agora separa:

- Dominus → IDPW;
- Dominus → Whats API;
- CURRENT runtime de eventos;
- TARGET SystemEvent/EventIngress;
- realtime global;
- media ownership.

### `PLAN.md`

O arquivo truncado após EVT-008 foi substituído pelo master plan completo, cobrindo:

```text
ARCH
DATA
EVENTS
MEDIA
PAGINATION
REALTIME
NOTIFICATIONS
OMNICHANNEL
ERROR UX
APP SHELL
MOBILE
MINHA EMPRESA
FUNCIONÁRIO DIGITAL
ORDER MANAGER
DASHBOARD
PROFILE
BACKEND/WA DECOMPOSITION
DESIGN SYSTEM
PERFORMANCE
PWA
TESTS
E2E
ACCESSIBILITY
OBSERVABILITY
LEGACY CLEANUP
DOCUMENTATION
```

### `TASKS.md`

O backlog foi sincronizado com evidências do branch. ARCH, DATA e EVT já implementados no branch são marcados como concluídos; fases seguintes permanecem pendentes.

“Concluído no branch” não significa necessariamente promoted/deployed em produção.

## 3. CURRENT vs TARGET

Documentos passaram a distinguir explicitamente:

```text
CURRENT RUNTIME
TARGET ARCHITECTURE
HISTORICAL ARTIFACT
MIGRATION SPEC
TECHNICAL INVENTORY
```

Isso evita tratar compatibilidade temporária como arquitetura final.

## 4. Histórico preservado sem autoridade

Mantidos como evidência:

```text
docs/refoundation/BASELINE.md
docs/refoundation/FALLBACK_AUDIT.md
docs/refoundation/EVT_CATALOG.md
docs/refoundation/CHECKPOINT_ARCH.md
docs/refoundation/CHECKPOINT_DATA.md
docs/refoundation/CHECKPOINT_EVENTS.md
docs/refoundation/EXECUTION_CONTRACTS.md
```

Esses arquivos possuem classificação explícita e não sobrescrevem GOAL/CONTRACTS/PLAN.

## 5. Migration specs

Arquivos como:

```text
N8N_ROUTER_SPEC.md
EVT_DEPRECATION.md
EVT_LEGACY_AUDIT.md
```

são auxiliares de execução, não arquitetura canônica.

## 6. Segurança documental

Foram removidos/redigidos dos documentos revisados:

- endereços de infraestrutura;
- portas/usuários administrativos;
- hostnames físicos desnecessários;
- IDs de workflow;
- IDs de container/aplicação;
- comandos específicos de operação real;
- issuer físico usado apenas como exemplo público.

A documentação usa placeholders e reserva topologia concreta para inventário/runbook privado.

## 7. Arquivos legacy

Artefatos antigos da raiz como `tasks.md`, `agents.md` e `TASK_DATA-003.yaml` já não concorrem com o Refoundation ativo.

Goals antigos dos serviços não foram apagados quando possuíam valor histórico; foram reduzidos e marcados explicitamente como históricos/superseded.

## 8. Limite importante desta correção

O branch `refactor/dominus-refoundation` e o histórico do repositório Whats API já continham mudanças não documentais feitas **antes** desta correção de documentação.

Esta correção não adicionou nem tentou validar/reverter essas mudanças funcionais. Elas devem ser revisadas separadamente antes de merge/promoção se ainda não tiverem sido auditadas.

## 9. Critérios finais

| Critério | Estado |
|---|---|
| README Dominus representa o produto | ✅ |
| Arquitetura global coerente | ✅ |
| IDPW = única autoridade M2M | ✅ |
| Whats API = Resource Server | ✅ |
| PLAN completo | ✅ |
| TASKS sincronizado com branch | ✅ |
| Session fallback documentado como proibido | ✅ |
| Realtime global documentado | ✅ |
| Media ownership documentado | ✅ |
| CURRENT vs TARGET explícito | ✅ |
| Goals antigos sem autoridade concorrente | ✅ |
| Documentação histórica classificada | ✅ |
| Topologia operacional removida/redigida dos documentos revisados | ✅ |
| Código alterado por esta correção | ❌ nenhum |

## 10. Próxima autoridade de execução

Para continuar o Refoundation:

```text
GOAL.md
  ↓
CONTRACTS.md
  ↓
PLAN.md
  ↓
TASKS.md
  ↓
checkpoint/evidence
```

A próxima fase estrutural pendente no backlog é **Media Ownership**, salvo decisão explícita de reordenamento pelo usuário.
