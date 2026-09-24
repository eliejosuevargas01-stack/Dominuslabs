# CHECKPOINT ARCH — 2026-09-24

## ARCH-000 — Congelar estado atual

**PARENT PLAN:** FASE 0 — INVENTÁRIO E BASELINE
**FILES:** `docs/refoundation/BASELINE.md`
**BEFORE:** Sem baseline documentado
**AFTER:** BASELINE.md com commit SHAs, workflows n8n, variáveis de ambiente, endpoints, eventos, suites de teste, 16 problemas conhecidos
**TESTS:** N/A (documentação)
**COMMIT:** `4c37fb6f`
**RISKS REMAINING:** Nenhum

---

## ARCH-001 — Inventário de fallbacks

**PARENT PLAN:** FASE 1 — AUDITORIA DE FALLBACKS E FAIL-CLOSED
**FILES:** `docs/refoundation/FALLBACK_AUDIT.md`
**BEFORE:** Sem inventário de fallbacks
**AFTER:** FALLBACK_AUDIT.md com 58 ocorrências classificadas nos 3 repos
**TESTS:** N/A (documentação)
**COMMIT:** `34b9dfdc`
**RISKS REMAINING:** Nenhum

---

## ARCH-002 — Configuração obrigatória

**PARENT PLAN:** FASE 1 — AUDITORIA DE FALLBACKS E FAIL-CLOSED
**FILES:** `project-hub/backend/app/core/startup_validator.py`, `project-hub/backend/app/core/config.py`, `project-hub/backend/app/main.py`, `project-hub/backend/tests/test_startup_validator.py`, `project-hub/backend/.env.example`
**BEFORE:** Backend iniciava sem validar configuração crítica
**AFTER:** Startup validation fail-closed com 21 testes; sem defaults sensíveis em config.py
**TESTS:** `python -m pytest tests/test_startup_validator.py` → 21/21 pass
**COMMIT:** `34b9dfdc`
**RISKS REMAINING:** Nenhum

---

## ARCH-003 — Remover defaults sensíveis

**PARENT PLAN:** FASE 1 — AUDITORIA DE FALLBACKS E FAIL-CLOSED
**FILES:** `docker-compose.yml`, `project-hub/backend/.env.example`, `project-hub/backend/app/core/config.py`
**BEFORE:** Defaults sensíveis em docker-compose (`admin123`, `dominuslabs-super-secret...`), placeholders com valores em `.env.example`, defaults em `config.py` (`localhost:3000`, `dominuslabs.online`, etc.)
**AFTER:** 
- docker-compose.yml: `${VAR:?required}` para todas as variáveis sensíveis
- .env.example: valores vazios
- config.py: sem defaults para ADMIN_USERNAME, VIEWER_USERNAME, WHATSAPP_API_URL, WHATSAPP_PUBLIC_URL, IDENTITY_WORKER_URL
**TESTS:** `npx tsc --noEmit` → 0 erros; `python3 -c "import ast; ast.parse(...)"` → OK
**COMMIT:** `0e4aefa5`
**RISKS REMAINING:** Nenhum

---

## ARCH-004 — Auditoria do .env versionado

**PARENT PLAN:** FASE 1 — AUDITORIA DE FALLBACKS E FAIL-CLOSED
**FILES:** `.env` (removido do tracking)
**BEFORE:** `.env` versionado com 7 variáveis sensíveis
**AFTER:** `.env` removido do tracking git (`git rm --cached`); `.env` já estava no `.gitignore`
**TESTS:** N/A
**COMMIT:** `a82e6e3f`
**RISKS REMAINING:** Secrets históricos no git history — recomendado rotacionar se necessário

---

## Aceite da Fase 1

- [x] nenhum secret crítico possui fallback funcional
- [x] startup falha sem config necessária
- [x] nenhum dado real de infraestrutura desnecessário permanece como default público
- [x] inventário de fallbacks produzido
- [x] valores demonstrativos de produção identificados
