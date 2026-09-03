# Implementation Plan - Backend Test Suite & Model Contract Stabilization

## 1. Contexto & Diagnóstico
Após as correções de segurança P0/P1 no backend, 63 dos 67 testes estão passando.
Restam 3 pontos de inconsistência identificados:
1. `app/models/product_media.py`: `product_id` foi tipado como `String`, quebrando o contrato com a tabela `produtos.id` (`UUID`) definido no Alembic `2026083001_create_company_product_tables.py` e validado por `test_database_models.py`.
2. `tests/test_product_media.py`: O mock de `get_db` isola a sessão mas não atende à checagem de permissão do `check_crm_permission`, resultando em 403 Forbidden.
3. `tests/test_whatsapp.py`: O teste `test_provision_whatsapp` faz mock direto em `httpx.AsyncClient`, enquanto o endpoint invoca `get_async_client(timeout=20.0, service_name="whatsapp")` de `app.core.http_client`.

## 2. Mudanças Técnicas

### 2.1. `project-hub/backend/app/models/product_media.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
...
    product_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="CASCADE"), index=True, nullable=False)
```

### 2.2. `project-hub/backend/tests/test_product_media.py`
Adicionar override de `check_crm_permission` em `app.dependency_overrides` para os testes de upload de imagem e vídeo.

### 2.3. `project-hub/backend/tests/test_whatsapp.py`
Atualizar o patch de `test_provision_whatsapp` para:
`@patch("app.api.endpoints.whatsapp.get_async_client")`

## 3. Validação
- `pytest project-hub/backend/tests/` -> 67 passed, 0 failed.
- Execução de Code Review e disparo de QA Jules.
