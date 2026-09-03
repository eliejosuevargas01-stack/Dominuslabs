# 👥 Agents & Governance: Frontend Media and Global Alarm Fixes

## 1. Rabibi-Maestro (Arquiteto & Planejador)
- Define a arquitetura das soluções e garante desacoplamento e conformidade com o padrão SPA do Vite.
- Estrutura os arquivos de contexto (`goal.md`, `agents.md`, `tasks.md`, `implementation_plan.md`).
- Delega a codificação para a VPS (`worker_create_thread`), monitora a telemetria e audita a qualidade via Code Review e QA.

## 2. Aider Workers (VPS)
- Executam a edição cirúrgica de código nos arquivos `src/pages/OmnichannelView.tsx` e `src/components/GlobalOrderNotification.tsx`.
- Garantem que testes unitários continuem 100% passando.

## 3. QA Jules (Validação Remota)
- Valida o candidato de release garantindo cobertura e ausência de regressões no frontend.
