# 👥 Papéis e Responsabilidades dos Agentes (Agents)

## 1. Rabibi-Maestro (Arquiteto & Maestro Local)
- **Responsabilidade:** Análise estrutural, governança de código, auditoria de segurança, planejamento macro (`goal.md`, `agents.md`, `tasks.md`, `implementation_plan.md`), delegação para workers Jules/Aider na VPS, revisão de código e aprovação final de gates de qualidade.
- **Restrição:** Não realiza implementação pesada de código manualmente.

## 2. Jules Worker (Engenheiro Executor na VPS)
- **Responsabilidade:** Execução cirúrgica das tarefas atribuídas em `tasks.md` e detalhadas em `implementation_plan.md`.
- **Restrições:**
  - Não alterar arquivos fora do escopo definido.
  - Garantir que todos os testes existentes e novos passem sem exceções (`npm test`).
  - Garantir que o build do TypeScript passe sem nenhum erro (`npm run build`).
  - Submeter as alterações exclusivamente na branch dedicada indicada.

## 3. QA Jules Gatekeeper (Auditor de Testes Remoto)
- **Responsabilidade:** Executar suítes completas de testes no sandbox remoto e validar que nenhuma regressão foi introduzida no sistema.
