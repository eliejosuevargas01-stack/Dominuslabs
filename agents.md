# 👥 Papéis e Responsabilidades dos Agentes (Agents)

## 1. Rabibi-Maestro (Arquiteto & Orquestrador Local)
- **Responsabilidade:** Planejamento arquitetural, governança de código, auditoria de segurança (SAST), orquestração de threads Aider, validação de gates de qualidade, execução de code review e promoção segura.

## 2. Aider Worker Threads na VPS
- **Responsabilidade:** Execução cirúrgica das tarefas atribuídas em `tasks.md` e `implementation_plan.md` no backend Python/FastAPI.
- **Restrições:**
  - Manter-se no escopo de arquivos definido.
  - Assegurar que os testes do pytest sejam executados e passem com sucesso.
  - Submeter as alterações na branch `fix/backend-security-and-contracts`.

## 3. QA Jules Gatekeeper (Auditor de Testes Remoto)
- **Responsabilidade:** Executar testes e validações no sandbox remoto como gate pré-produção.
