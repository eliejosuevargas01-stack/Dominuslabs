# 🎯 Macro Goal: Estabilidade e Resiliência do Sistema (FastAPI, SSE e Omnichannel)

## 📌 Contexto e Problema
O sistema sofria degradação progressiva após o carregamento inicial ("no início carrega, mas depois cai tudo"). A investigação com Deep Research comprovou que o problema decorria de:
1. Uma avalanche de 50 requisições simultâneas de avatares e mídias disparada pelo frontend ao renderizar o histórico de conversas do WhatsApp.
2. Cada requisição de mídia/avatar inexistente tentava até 6 caminhos externos no backend com timeouts longos (acumulando mais de 90 segundos por requisição), saturando por completo os workers do Uvicorn e bloqueando endpoints essenciais como `/orders`, `/projects` e autenticação.
3. Conexões de Server-Sent Events (SSE) sem tratamento de cancelamento imediato gerando falso erro de CORS no navegador quando o servidor engasgava.
4. Falta de interrupção do som de alerta de novos pedidos no PDV ao aceitar ou rejeitar pedidos.

---

## 🎯 Requisitos e Critérios de Aceitação

1. **Eliminação da Tempestade de Avatares no Frontend:**
   - A lista de conversas da sidebar no Omnichannel deve carregar imagens diretas da CDN da Meta quando disponíveis (`pps.whatsapp.net`, `fbcdn.net`, `data:image`).
   - Para contatos sem foto direta, utilizar exclusivamente o componente visual com as iniciais do contato (`avatar-fallback`), com **zero requisições de proxy** para a VPS durante a renderização da sidebar.
   - O proxy de avatar dinâmico só deve ser acionado sob demanda caso o usuário abra um chat específico no cabeçalho ativo.

2. **Timeout Rígido e Circuit Breaker no Backend FastAPI:**
   - Em `app/main.py` e `app/api/endpoints/whatsapp.py`, as rotas `/avatar` e `/media` devem ter timeout estrito de **3.0 segundos**.
   - Mídias ou avatares inexistentes devem responder com `404 Not Found` em milissegundos, sem segurar as conexões do servidor.
   - O container da VPS deve manter o Uvicorn configurado com **4 workers concorrentes** (`--workers 4`).

3. **Governança Estrita de Conexões SSE:**
   - Toda rota SSE (`StreamingResponse`) deve checar `await request.is_disconnected()` a cada iteração e desalocar listeners no bloco `finally`.
   - O frontend deve fechar explicitamente a conexão (`eventSource.close()`) no evento `onerror` para evitar reconnect storms.

4. **Regras de Negócio do Order Manager:**
   - O som/alarme sonoro de notificação de pedido deve cessar imediatamente no momento em que o operador clica em **Aceitar** ou **Rejeitar**.
   - Integração com Waze e payload de pedido formatado corretamente com os campos recebidos do webhook.
