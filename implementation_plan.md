# 📐 Plano de Implementação Arquitetural (Implementation Plan)

## 1. Visão Geral
Este plano especifica as correções estritas e pontuais que os workers devem executar no código-fonte do Frontend para restabelecer a integridade de compilação, testes e conformidade com as diretrizes de segurança do Rabibi-Maestro.

---

## 2. Especificação Técnica por Arquivo

### 2.1 `src/components/GlobalOrderNotification.tsx`
- **Problema:** A linha 139 avalia `audioContextRef.current.state === 'running'` dentro de um bloco `if (audioContextRef.current?.state === 'suspended')`. O compilador TS estreitou o tipo para `"suspended"`, acusando TS2367.
- **Correção:** Realizar type assertion seguro:
  ```typescript
  if ((audioContextRef.current.state as string) === 'running') {
  ```

### 2.2 `src/App.test.tsx`
- **Problema:** Os testes falham porque o matcher `toBeInTheDocument` não foi estendido no `expect` do Vitest para este arquivo.
- **Correção:** Adicionar a importação no topo de `src/App.test.tsx`:
  ```typescript
  import '@testing-library/jest-dom';
  ```

### 2.3 `vite.config.ts`
- **Problema:** O Vitest roda testes que residem em `test-integration/` por padrão, causando parsing errors do eslint e duplicidade de testes.
- **Correção:** No bloco `test` do `vite.config.ts`, definir `exclude`:
  ```typescript
  test: {
    environment: 'jsdom',
    globals: true,
    exclude: ['**/node_modules/**', '**/dist/**', '**/test-integration/**'],
  }
  ```

### 2.4 Purga de `tranzinc`
- Substituir todas as ocorrências de `tranzinc` por `translate`:
  - `tranzinc-x-5` -> `translate-x-5`
  - `tranzinc-x-0` -> `translate-x-0`
  - `-tranzinc-y-1/2` -> `-translate-y-1/2`
- Em `src/pages/OmnichannelView.tsx`, restaurar:
  ```tsx
  <button
    onClick={() => setSearchTerm('')}
    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 rounded-full p-1 cursor-pointer"
    aria-label="Limpar pesquisa"
    title="Limpar pesquisa"
  >
    <X className="w-3.5 h-3.5" />
  </button>
  ```

### 2.5 `src/App.tsx`
- Remover as linhas 278-285 que declaram a rota duplicada `/order-manager` sem layout:
  ```tsx
  <Route
    path="/order-manager"
    element={
      <ProtectedRoute>
        <OrderManagerView />
      </ProtectedRoute>
    }
  />
  ```

### 2.6 `src/pages/OrderManagerView.tsx`
- Em `handleAccept`, `handleReject` e `handleStatusChange`:
  - Enviar cabeçalho `Authorization: Bearer ${token}`.
  - Remover `?token=...` dos URLs de mutação REST.
  - No `handleReject`: adicionar `stopAlarm(orderId)` antes da chamada de rede para parar o alarme de áudio.

---

## 3. Critérios de Validação Final
- `npm test`: Todos os testes devem passar (código 0).
- `npm run build`: O build do TypeScript e do Vite devem passar (código 0).
