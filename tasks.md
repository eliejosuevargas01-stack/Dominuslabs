# 📋 Tarefas Desmembradas para Execução (Tasks)

### Tarefa 1: Desbloqueio do Compilador TypeScript & Build
- **Arquivo:** `src/components/GlobalOrderNotification.tsx`
- **Ação:** Corrigir a comparação de tipo TS2367 em `audioContextRef.current.state === 'running'` utilizando cast apropriado `((audioContextRef.current.state as string) === 'running')`.
- **Validação:** Rodar `npm run build` e confirmar que `tsc -b` completa com sucesso.

### Tarefa 2: Estabilização dos Testes Unitários do `App.tsx`
- **Arquivo:** `src/App.test.tsx` e `vite.config.ts`
- **Ação:**
  - Adicionar `import '@testing-library/jest-dom';` em `src/App.test.tsx`.
  - Configurar `vite.config.ts` para excluir `test-integration/**` da execução dos testes do Vitest.
- **Validação:** Rodar `npm test` e verificar se os 5 testes de `ProtectedRoute` passam com 100% de sucesso.

### Tarefa 3: Purga da Classe Inválida `tranzinc` e Restauração de Acessibilidade
- **Arquivos:**
  - `src/pages/AutomationsView.tsx` (restaurar `translate-x-5` e `translate-x-0`)
  - `src/pages/CompanySettingsView.tsx` (restaurar `-translate-y-1/2`)
  - `src/pages/CrmView.tsx` (restaurar `-translate-y-1/2`)
  - `src/pages/OmnichannelView.tsx` (restaurar `-translate-y-1/2`, `aria-label="Limpar pesquisa"`, título e focus ring)
  - `src/pages/Showcase.tsx` (restaurar `-translate-y-1/2`)
- **Validação:** Checar via grep se qualquer resíduo de `tranzinc` permanece no repositório.

### Tarefa 4: Limpeza de Rotas Duplicadas e Vazamento de Tokens
- **Arquivos:**
  - `src/App.tsx`: Remover a rota duplicada `<Route path="/order-manager" ...>` nas linhas finais, mantendo a rota principal envelopada com `DashboardLayout`.
  - `src/pages/OrderManagerView.tsx`:
    - Garantir que `handleAccept`, `handleReject` e `handleStatusChange` utilizem o header `Authorization: Bearer ${token}` em vez de passar o token na query string `?token=...`.
    - Fazer com que `handleReject` chame `stopAlarm(orderId)` para encerrar o áudio sonoro ao recusar.
