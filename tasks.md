# 📋 Tarefas Desmembradas para Execução no Backend (Tasks)

### Tarefa 1: Sanitização de Path Traversal em Uploads (P0)
- **Arquivo:** `project-hub/backend/app/api/endpoints/uploads.py`
- **Ação:** Sanitizar os caminhos recebidos em `get_uploaded_file` usando `os.path.realpath` e `os.path.commonpath`, garantindo que qualquer tentativa de navegação fora de `settings.UPLOAD_DIR` retorne HTTP 403 ou 404.

### Tarefa 2: Isolamento Multi-Tenant e Autenticação no SSE de Chats (P0)
- **Arquivo:** `project-hub/backend/app/api/endpoints/webhooks.py`
- **Ação:**
  - Exigir token JWT válido para conexão ao endpoint `/events/crm-chats`. Rejeitar conexões anônimas com HTTP 401.
  - Armazenar o `tenant_id` do usuário conectado na estrutura de ouvintes.
  - Em `notify_crm_chat_listeners`, despachar mensagens exclusivamente para ouvintes que pertençam ao mesmo `tenant_id` do evento.

### Tarefa 3: Implementação do Endpoint `/reject` e Transições de Status de Pedidos (P1)
- **Arquivo:** `project-hub/backend/app/api/endpoints/orders.py`
- **Ação:**
  - Atualizar `ORDER_STATUS_TRANSITIONS` para permitir que `"pending"` transite para `{"accepted", "rejected"}`.
  - Implementar o endpoint `POST /orders/{order_id}/reject` que aceita autenticação via header `Authorization: Bearer <token>`, valida a transição e atualiza o pedido para `"rejected"`.

### Tarefa 4: Autenticação em Mídia de Produtos e Sincronização de URLs (P0/P1)
- **Arquivos:**
  - `project-hub/backend/app/api/endpoints/product_media.py`: Adicionar dependência de autenticação `current_user: User = Depends(get_current_active_user)` no upload e padronizar URLs retornadas.
  - `project-hub/backend/app/main.py`: Montar `/uploads` e `/api/uploads` de forma consistente.

### Tarefa 5: Correção de Ciclo de Vida do SQLAlchemy em Background Tasks (P1)
- **Arquivo:** `project-hub/backend/app/api/endpoints/auth.py`
- **Ação:** Criar sessões independentes dentro das funções que rodam em background (`SessionLocal()`), fechando-as em bloco `finally`, em vez de reaproveitar a sessão fechada da requisição HTTP.
