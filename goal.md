# 🎯 Macro Goal: Correção de Bugs e Estabilização do Frontend e Contratos

## 📌 Objetivo Macro
Corrigir todos os problemas críticos (P0), regressões funcionais (P1) e defeitos de interface/Tailwind (P2) identificados na auditoria do Rabibi-Maestro no frontend do Dominuslabs, garantindo 100% de aprovação nos testes (`vitest`), compilação limpa do TypeScript (`tsc -b`) e build de produção (`vite build`).

---

## ✅ Critérios de Aceitação

1. **Build de Produção & TypeScript:**
   - O comando `npm run build` (`tsc -b && vite build`) deve executar com código de saída 0 (sem erros de compilação TS).
   - O erro TS2367 em `src/components/GlobalOrderNotification.tsx` deve ser corrigido com cast adequado do estado do AudioContext (`(audioContextRef.current.state as string) === 'running'`).

2. **Suíte de Testes Automatizados:**
   - O comando `npm test` (`vitest run`) deve rodar com 100% dos testes passando em todos os arquivos de teste.
   - `src/App.test.tsx` deve importar `@testing-library/jest-dom` para que `toBeInTheDocument` funcione adequadamente.
   - O setup do Vitest em `vite.config.ts` deve excluir `test-integration/**` e fornecer matchers globais do DOM.

3. **Correção de Estilos Tailwind CSS Corrompidos (`tranzinc`):**
   - Restaurar todas as ocorrências acidentais de `tranzinc` para suas classes legítimas do Tailwind (`translate-x-5`, `-translate-y-1/2`, etc.) nos arquivos:
     - `src/pages/AutomationsView.tsx`
     - `src/pages/CompanySettingsView.tsx`
     - `src/pages/CrmView.tsx`
     - `src/pages/OmnichannelView.tsx`
     - `src/pages/Showcase.tsx`
   - Restaurar os atributos de acessibilidade (`aria-label="Limpar pesquisa"`, título e focus ring) no botão de limpar busca de `OmnichannelView.tsx`.

4. **Integridade de Rotas e Componentes:**
   - Remover a declaração duplicada da rota `/order-manager` em `src/App.tsx`.
   - Garantir que `GlobalOrderNotification` esteja devidamente integrado ou referenciado de forma consistente sem vazar tokens em query parameters.
   - Proteger chamadas HTTP contra vazamento de tokens em URLs (`Authorization: Bearer <token>` em vez de `?token=...`) nas requisições REST do `OrderManagerView.tsx`.
   - Garantir que `handleReject` no `OrderManagerView.tsx` silencie o alarme sonoro (`stopAlarm(orderId)`).
