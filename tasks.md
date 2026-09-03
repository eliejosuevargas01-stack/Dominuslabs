# 📋 Tasks: Plano de Execução e Distribuição

## Tarefa 1: Proteção e Blindagem de Avatares no Frontend (Omnichannel)
- **Responsável:** Worker-Frontend
- **Ações:**
  - Atualizar `getAvatarSrc` em `src/pages/OmnichannelView.tsx` adicionando a flag `allowProxy=false` para itens da lista na sidebar.
  - Assegurar que imagens diretas da CDN (`pps.whatsapp.net`, `fbcdn.net`, `data:image`) continuem sendo exibidas.
  - Para contatos sem imagem direta, renderizar exclusivamente o fallback de iniciais com cores dinâmicas, sem efetuar requisições HTTP contra o backend.
  - No cabeçalho da conversa aberta, permitir a tentativa sob demanda via proxy (`allowProxy=true`).

## Tarefa 2: Timeouts Rígidos e Circuit Breaker no Backend (FastAPI)
- **Responsável:** Worker-Backend
- **Ações:**
  - Reduzir timeout de `make_whatsapp_api_request` nas rotas `/avatar` e `/media` para 3.0 segundos.
  - Eliminar o loop de 6 caminhos sequenciais em `root_avatar_proxy`, focando exclusivamente na rota canônica da sessão.
  - Garantir resposta rápida `404 Not Found` em falha ou timeout, sem segurar conexões dos workers ASGI.

## Tarefa 3: Governança de Conexões SSE e Tratamento de Desconexão
- **Responsável:** Worker-Backend & Worker-Frontend
- **Ações:**
  - Validar e garantir `await request.is_disconnected()` em todas as rotas SSE (`/webhooks/events`, `/webhooks/events/crm-chats`).
  - No frontend, assegurar o encerramento imediato via `eventSource.close()` no evento `onerror` em todos os dashboards e visualizadores.

## Tarefa 4: Controle de Áudio e Alarme no Order Manager
- **Responsável:** Worker-Frontend
- **Ações:**
  - Garantir que o alarme sonoro pare instantaneamente quando qualquer pedido for Aceito ou Rejeitado no PDV.
  - Validar renderização dos dados do novo payload de pedidos e links de navegação para o Waze.

## Tarefa 5: Homologação e Gates de Qualidade
- **Responsável:** Jules QA & Rabibi-Maestro
- **Ações:**
  - Executar suíte de testes unitários (`npm test` / Vitest).
  - Validar build de produção (`npm run build`).
  - Executar auditoria de rotas e console via Chrome DevTools MCP.
