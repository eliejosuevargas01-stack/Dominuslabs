# 🛠️ Implementation Plan: Frontend Media & Global Alarm Stabilization

## 1. Contexto & Problema
No ambiente de produção (`https://dominuslabs.onrender.com`):
1. O chat de WhatsApp (`OmnichannelView.tsx`) tenta tocar áudios e carregar fotos usando caminhos relativos como `/api/whatsapp/sessions/{session}/media`. Como o Render serve apenas o SPA compilado, a requisição devolve o `index.html` do Vite com HTTP 200, quebrando tags `<audio>` e `<img>`. Além disso, a rota requer o parâmetro `?token=...` validado pelo backend.
2. O componente `GlobalOrderNotification.tsx` possui fallbacks estáticos `ws://localhost:8000` e `http://localhost:8000/api/v1`, inundando o console com erros de CORS e desconexões contínuas a cada 5 segundos.

## 2. Solução Arquitetural

### Modificações em `src/pages/OmnichannelView.tsx`:
- Importar `API_BASE` de `../services/api`.
- Definir helper seguro para extrair o token do usuário:
  ```typescript
  const getToken = () => localStorage.getItem('admin_token') || '';
  ```
- Atualizar `getMediaUrl`:
  - Se a URL já for externa absoluta (`http://`, `https://`, `data:`), manter.
  - Se for rota de proxy de mídia, prefixar com a base do backend (`API_BASE.replace(/\/api\/v1\/?$/, '')`) e rota `/api/v1/whatsapp/sessions/${sessId}/media?messageId=${msgId}&token=${getToken()}`.
- Atualizar `getAvatarUrl`:
  - Utilizar rota oficial do backend: `${API_BASE}/whatsapp/sessions/${targetSession}/avatar?jid=${encodeURIComponent(targetJid)}&token=${getToken()}`.

### Modificações em `src/components/GlobalOrderNotification.tsx`:
- Importar `API_BASE` de `../services/api`.
- Resolver a URL do WebSocket a partir de `API_BASE`:
  ```typescript
  const getWebSocketUrl = () => {
    if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
    const baseWithoutApi = API_BASE.replace(/\/api\/v1\/?$/, '');
    const wsProto = baseWithoutApi.startsWith('https') ? 'wss:' : 'ws:';
    const host = baseWithoutApi.replace(/^https?:\/\//, '');
    return `${wsProto}//${host}`;
  };
  ```
- Atualizar a montagem do WebSocket para `${getWebSocketUrl()}/api/v1/orders/ws?token=${token}`.
- Atualizar `fetchOrders` para usar `${API_BASE}/orders`.

## 3. Plano de Verificação
1. Executar bateria de testes com Vitest:
   `npm test -- --run`
2. Validar que nenhum teste existente foi quebrado.
3. Submeter à auditoria de Code Review do Dominus-MCP.
