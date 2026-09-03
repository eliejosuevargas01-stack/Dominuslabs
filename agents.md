# Multi-Agent Coordination & Responsibilities

## 1. Rabibi-Maestro (Architect & Orchestrator)
- Governança de arquitetura e padrões (SOLID, Zero-Trust, desacoplamento Node/FastAPI).
- Definição dos contratos de modelo SQLAlchemy vs migrações Alembic.
- Orquestração de threads no Dominus-MCP, revisão de código e gate de QA Jules.

## 2. Aider Worker Agents (Autonomous Coders na VPS)
- **Worker 1 (`align-product-media-model`):**
  - Alinhar `project-hub/backend/app/models/product_media.py` com o Alembic, definindo `product_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="CASCADE"), index=True, nullable=False)`.
- **Worker 2 (`fix-test-mocks`):**
  - Ajustar mock de `check_crm_permission` em `project-hub/backend/tests/test_product_media.py`.
  - Ajustar mock do cliente HTTP assíncrono em `project-hub/backend/tests/test_whatsapp.py:test_provision_whatsapp`.

## 3. QA Jules (Autonomous Verifier)
- Verificação do repositório remoto, execução do sandbox de testes e validação de cobertura.
