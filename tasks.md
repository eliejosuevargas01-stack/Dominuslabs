# 📋 Tasks: Frontend Media and Global Alarm Fixes

## Tarefa 1: Corrigir URLs de Mídia e Avatar no Omnichannel
- **Arquivo:** `src/pages/OmnichannelView.tsx`
- **Ações:**
  1. No método `getMediaUrl(msg, defaultSessionId)`:
     - Importar `API_BASE` de `../services/api` ou construir a URL base a partir dele.
     - Obter o token JWT do localStorage (`admin_token`).
     - Em vez de retornar uma URL relativa `/api/whatsapp/sessions/...`, compor com a URL do backend: `${API_BASE}/whatsapp/sessions/${encodeURIComponent(sessId)}/media?messageId=${encodeURIComponent(msgId)}&token=${encodeURIComponent(token || '')}`.
     - Tratar links existentes e garantir que URLs relativas legadas `/api/sessions/` ou `/api/whatsapp/sessions/` recebam o prefixo da API do backend e o parâmetro `token`.
  2. No método `getAvatarUrl(session_id, jid, url)`:
     - Obter o token do localStorage (`admin_token`).
     - Se `targetJid` existir, retornar `${API_BASE}/whatsapp/sessions/${encodeURIComponent(targetSession)}/avatar?jid=${encodeURIComponent(targetJid)}&token=${encodeURIComponent(token || '')}`.
     - Se for URL da Meta (`pps.whatsapp.net`), manter como alternativa ou fornecer fallback para o proxy do backend caso falhe.

## Tarefa 2: Corrigir Resolução Dinâmica de URL e WebSocket no Alarme Global
- **Arquivo:** `src/components/GlobalOrderNotification.tsx`
- **Ações:**
  1. Importar `API_BASE` e `getDynamicApiUrl` de `../services/api`.
  2. Construir dinamicamente a `WEBSOCKET_URL`:
     - Se `import.meta.env.VITE_WS_URL` existir, usar.
     - Caso contrário, converter a base HTTP de `API_BASE` para WebSocket: substituir `https://` por `wss://` e `http://` por `ws://`, removendo `/api/v1` da cauda se necessário, de modo que `API_BASE = "https://dominuslabs.online/api/v1"` gere `wss://dominuslabs.online/api/v1/orders/ws`.
  3. No `fetchOrders`:
     - Usar `${API_BASE}/orders` em vez de `http://localhost:8000/api/v1/orders`.
  4. Garantir que nenhuma tentativa de conexão com `localhost:8000` ocorra quando a aplicação estiver rodando fora do ambiente local.
