# 📋 Code Review Human Backlog

Itens de melhoria não-bloqueantes identificados durante a revisão de código pelo Dominus-MCP (`code_review`) e arquiteto Rabibi-Maestro.

---

### 1. Atualização em Lote de Leads no CRM (Batch Processing)
* **Commit:** `f6fb177a`
* **Arquivo:** `src/pages/CrmView.tsx:L66-L72`
* **Evidência:** Disparo de múltiplas requisições `PUT` simultâneas com `Promise.allSettled(...)` para atualizar contatos que avançam de status.
* **Impacto Potencial:** Se houver um volume muito grande de leads, pode haver saturação do pool de conexões HTTP do navegador e rate limiting no backend.
* **Ação Sugerida:** Criar rota de mutação em lote (`PUT /api/v1/crm/leads/bulk`) no backend ou processamento automático no carregamento.

---

### 2. Backoff Exponencial com Jitter no WebSocket de Pedidos
* **Commit:** `f6fb177a`
* **Arquivo:** `src/pages/OrderManagerView.tsx:L108-L111`
* **Evidência:** Reconexão com intervalo fixo `reconnectTimer = setTimeout(connect, 5000)`.
* **Impacto Potencial:** Efeito "Thundering Herd" caso múltiplos terminais PDV tentem reconectar simultaneamente após instabilidade de rede.
* **Ação Sugerida:** Implementar backoff exponencial com jitter (ex: 2s, 4s, 8s com randomização).

---

### 3. Refatoração de Tipagem no Fallback de Áudio
* **Commit:** `f6fb177a`
* **Arquivo:** `src/components/GlobalOrderNotification.tsx:L114`
* **Evidência:** Uso de `(oscillatorRef.current as any)._pulseInterval` para armazenar o ID do `setInterval`.
* **Impacto Potencial:** Uso de `any` em tipagem estática.
* **Ação Sugerida:** Utilizar `useRef<number | null>(null)` para armazenar a referência do intervalo do pulso sonoro.
