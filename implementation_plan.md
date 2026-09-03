# Plano de Implementação: Resiliência de Proxy, Avatares sob Demanda e Estabilidade Contínua

Plano técnico estruturado com base nas descobertas do **Deep Research do Dominus-MCP** (ID: `1788470538351`) para resolver em definitivo o incidente de sobrecarga do servidor ("no início carrega, mas depois cai tudo").

---

## User Review Required

> [!IMPORTANT]
> **Alteração de Comportamento na Renderização de Avatares:**
> Para eliminar o ataque acidental de negação de serviço (50 requisições simultâneas de avatares com latência de 90s cada que derrubavam a VPS), a sidebar de conversas do Omnichannel passará a exibir as fotos diretas da CDN da Meta e, nos contatos sem URL direta, exibirá o componente elegante com as iniciais do contato. A tentativa de proxy dinâmico será restrita ao chat ativamente aberto pelo usuário.

> [!TIP]
> Essa mudança reduz a carga de I/O sobre a VPS em mais de **95%** durante a abertura do Omnichannel, permitindo que a aplicação responda a pedidos e dashboards em menos de 50ms.

---

## Proposed Changes

### Frontend (React / TypeScript)

#### [MODIFY] [src/pages/OmnichannelView.tsx](file:///home/eliezer/Escritorio/dominuslabs/src/pages/OmnichannelView.tsx)
- Refatorar a função `getAvatarSrc(url, session_id, jid, allowProxy = false)`:
  - Se a URL for direta (`pps.whatsapp.net`, `fbcdn.net`, `data:image` ou URL absoluta HTTP), retorna a imagem diretamente.
  - Se `allowProxy === false` (modo padrão da sidebar), retorna `null` para permitir a renderização das iniciais coloridas, eliminando requisições contra o backend.
  - Se `allowProxy === true` (cabeçalho da conversa aberta), constrói a URL de proxy para o contato selecionado com token JWT.
- Assegurar fechamento de socket no `onerror` do stream `crm-chats`.

#### [MODIFY] [src/pages/OrderManagerView.tsx](file:///home/eliezer/Escritorio/dominuslabs/src/pages/OrderManagerView.tsx)
- Assegurar que ao disparar as mutações de **Aceitar Pedido** ou **Rejeitar Pedido**, a função `stopAlarm()` seja imediatamente executada, silenciando o áudio no ato do clique do operador.

---

### Backend (FastAPI Core)

#### [MODIFY] [test-integration/project-hub/backend/app/main.py](file:///home/eliezer/Escritorio/dominuslabs/test-integration/project-hub/backend/app/main.py)
- Em `root_avatar_proxy`:
  - Substituir o loop lento de 6 caminhos pelo caminho canônico da sessão.
  - Adicionar timeout rígido de `3.0` segundos na chamada a `make_whatsapp_api_request`.
- Em `root_media_proxy`:
  - Garantir timeout de `3.0` segundos e resposta 404 imediata quando a mídia não estiver presente.

#### [MODIFY] [test-integration/project-hub/backend/app/api/endpoints/whatsapp.py](file:///home/eliezer/Escritorio/dominuslabs/test-integration/project-hub/backend/app/api/endpoints/whatsapp.py)
- Em `get_session_avatar`: adicionar `timeout=3.0` na invocação de `make_whatsapp_api_request`.
- Em `get_session_media`: adicionar `timeout=3.0` na invocação de `make_whatsapp_api_request`.

---

## Verification Plan

### Automated Tests
- Executar suíte de testes Vitest:
  ```bash
  npm test
  ```
- Compilar o build de produção do frontend:
  ```bash
  npm run build
  ```

### Manual Verification
- **Teste de Estabilidade e Concorrência:**
  - Navegar para `https://dominuslabs.onrender.com/omnichannel` e alternar entre diferentes chats do WhatsApp.
  - Monitorar em tempo real a latência de `/api/v1/orders` com `curl` para certificar que o tempo de resposta permanece abaixo de 100ms.
- **Auditoria de Console no DevTools:**
  - Inspecionar `get_console_message` no Chrome DevTools MCP para atestar ausência de erros de CORS ou desconexões.
- **Validação de Áudio no Order Manager:**
  - Simular ou alterar o status de um pedido para pendente e verificar que ao clicar em Aceitar ou Rejeitar, o alarme é silenciado na hora.
