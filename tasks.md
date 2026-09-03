# Tasks Breakdown

- [ ] **Task 1: Alinhar Modelo ProductMedia com Alembic e Schema PostgreSQL**
  - Arquivo: `project-hub/backend/app/models/product_media.py`
  - Restaurar importações de `ForeignKey` e `from sqlalchemy.dialects.postgresql import UUID`.
  - Definir `product_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="CASCADE"), index=True, nullable=False)`.

- [ ] **Task 2: Corrigir Mock de Autenticação/Permissão em Product Media Tests**
  - Arquivo: `project-hub/backend/tests/test_product_media.py`
  - Incluir override de `check_crm_permission` para permitir execução limpa dos endpoints de upload sem rejeição por usuário mock.

- [ ] **Task 3: Corrigir Mock de Cliente Assíncrono em WhatsApp Provision Test**
  - Arquivo: `project-hub/backend/tests/test_whatsapp.py`
  - Patchear `app.api.endpoints.whatsapp.get_async_client` retornando o contexto assíncrono com mock de post 200.
