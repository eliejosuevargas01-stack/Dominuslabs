# 👥 Agents: Papéis, Responsabilidades e Restrições

## 1. Rabibi-Maestro (Arquiteto e Orquestrador)
- **Papel:** Planejamento arquitetural, governança de código, garantia das diretrizes SOLID e desacoplamento (Node.js BFF vs FastAPI Core).
- **Restrições:** Não realiza codificação pesada na máquina de desenvolvimento; delega tarefas através de branches isoladas e valida a conformidade com Code Review e QA.

## 2. Worker-Frontend (Especialista em React/TypeScript & UX)
- **Papel:** Otimização de performance de interface, carregamento seletivo de avatares, áudio sob demanda (`preload="none"`), tratamento de reconexão de SSE e controle do alarme sonoro do PDV.
- **Escopo de Arquivos:** `src/pages/OmnichannelView.tsx`, `src/pages/OrderManagerView.tsx`, `index.html`.
- **Restrições:** Não alterar contratos de autenticação ou schemas de dados sem validação prévia.

## 3. Worker-Backend (Especialista em FastAPI, Concorrência e Resiliência)
- **Papel:** Implementação de timeouts estritos em rotas de proxy, verificação de `request.is_disconnected()` em streams SSE, configuração de múltiplos workers ASGI e isolamento de integrações externas.
- **Escopo de Arquivos:** `test-integration/project-hub/backend/app/main.py`, `test-integration/project-hub/backend/app/api/endpoints/whatsapp.py`, `test-integration/project-hub/backend/app/api/endpoints/webhooks.py`.
- **Restrições:** Jamais utilizar chamadas síncronas bloqueantes dentro de rotas `async def`.

## 4. Jules QA & Code Reviewer (Gatekeepers de Qualidade)
- **Papel:** Execução de testes de regressão, análise estática de segurança e verificação de bloqueadores P0/P1 antes de qualquer autorização de deploy.
- **Restrições:** Travamento absoluto contra deploys automáticos em produção sem consentimento explícito do usuário.
