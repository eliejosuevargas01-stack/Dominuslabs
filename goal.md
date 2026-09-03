# Macro Goal: Backend Test Suite & Model Contract Stabilization

## Objetivo Principal
Completar a estabilização de 100% dos testes unitários do backend (`project-hub/backend`), alinhando o modelo SQLAlchemy `ProductMedia` com a migration PostgreSQL do Alembic (chave estrangeira e tipo UUID), corrigindo o mock do cliente HTTP assíncrono em `test_provision_whatsapp` e o mock de permissão CRM no teste de upload de mídia de produtos.

## Critérios de Aceite
1. Modelo `ProductMedia` restaurado com `UUID(as_uuid=True)` e `ForeignKey("produtos.id", ondelete="CASCADE")` alinhado à migration Alembic `2026083001_create_company_product_tables.py` e ao teste `test_database_models.py`.
2. `tests/test_product_media.py` com dependência de permissão devidamente ajustada para validar uploads de imagens e vídeos com status 200.
3. `tests/test_whatsapp.py:test_provision_whatsapp` corrigido para interceptar o cliente assíncrono real utilizado pelo endpoint (`get_async_client`), passando com sucesso.
4. Execução completa do pytest sem nenhuma falha (67/67 testes aprovados).
5. Gate de Code Review e acionamento de validação QA Jules.
