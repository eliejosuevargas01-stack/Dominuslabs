# 🎯 Macro Goal: Correção de Segurança, Contratos e Confiabilidade no Backend

## 📌 Objetivo Macro
Resolver todas as vulnerabilidades críticas de segurança (P0), quebras de contrato de API (P1), sessões quebradas do SQLAlchemy e integridade arquitetural na camada Backend (`project-hub/backend/`), garantindo que todos os testes do pytest passem e a aplicação atenda aos guardrails do Rabibi-Maestro.

---

## ✅ Critérios de Aceitação

1. **Path Traversal / LFI Sanitizado (P0):**
   - Em `project-hub/backend/app/api/endpoints/uploads.py`, sanitizar parâmetros `{subfolder}` e `{filename}` garantindo que o caminho resolvido esteja estritamente contido dentro de `settings.UPLOAD_DIR` sem permitir sequências de escape (`..`).

2. **Isolamento Multi-Tenant e Autenticação no SSE de Mensagens (P0):**
   - Em `project-hub/backend/app/api/endpoints/webhooks.py`, o endpoint `/events/crm-chats` deve exigir autenticação obrigatória (rejeitar conexões anônimas não autorizadas).
   - O dispatcher `notify_crm_chat_listeners` deve filtrar ouvintes estritamente pelo `tenant_id` da empresa, impedindo que mensagens de clientes vazem para outros inquilinos.

3. **Autenticação no Upload de Mídia de Produtos (P0):**
   - Em `project-hub/backend/app/api/endpoints/product_media.py`, o endpoint `POST /product-media/` deve exigir autenticação (`current_user`).

4. **Implementação do Contrato `/reject` de Pedidos (P1):**
   - Em `project-hub/backend/app/api/endpoints/orders.py`, implementar o endpoint `POST /api/v1/orders/{order_id}/reject` que aceita `Authorization: Bearer <token>` e atualiza o status do pedido para `"rejected"`.
   - Atualizar a máquina de estados `ORDER_STATUS_TRANSITIONS` para permitir transição de `"pending"` para `{"accepted", "rejected"}`.

5. **Sincronização de URLs de Mídia de Produtos (P1):**
   - Alinhar a URL gerada por `product_media.py` com a montagem estática do FastAPI em `app/main.py`.

6. **Ciclo de Vida de Sessões do SQLAlchemy em Background Tasks (P1):**
   - Em `project-hub/backend/app/api/endpoints/auth.py`, criar uma nova sessão do banco usando `SessionLocal()` dentro das tarefas de background (`_maybe_provision`), evitando uso de sessões fechadas pelo ciclo de requisição HTTP.

7. **Restauração de Payloads Aninhados em Webhooks:**
   - Em `project-hub/backend/app/api/endpoints/webhooks.py`, restaurar o helper para tratar webhooks com strings JSON serializadas e formulários (`application/x-www-form-urlencoded`).
