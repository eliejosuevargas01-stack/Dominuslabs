# Relatório de Bugs: Análise de Comunicação Backend-Frontend

Este documento documenta os bugs identificados e corrigidos durante a análise da comunicação e esquemas entre o frontend em React/TypeScript e o backend em FastAPI do Project Hub.

## Bugs Encontrados e Resolvidos

### 1. Desalinhamento e Tipagem Fraca de Dados no Frontend (`src/pages/CrmView.tsx`, `src/pages/LeadDetailView.tsx`, `src/pages/OmnichannelView.tsx`)
**Descrição:**
As lógicas de visualização de CRM e Omnichannel no frontend usavam explicitamente o tipo `any` ou arrays sem tipagem formal (`any[]`) para tratar as respostas dos endpoints do backend, especificamente para `Leads` e `Conversas`. Por depender da estrutura de banco não validada mapeada pela API `n8n_service.py` (`lead.get("id") or lead.get("lead_id")`), o frontend realizava múltiplas leituras flexíveis e desordenadas das chaves dos objetos sem garantias estáticas de TypeScript, o que poderia levar a perdas de informação, *undefined crashes* em renderizações dinâmicas e violação das definições estritas nos schemas Pydantic no Backend (`project-hub/backend/app/schemas/crm.py`).
**Ação Tomada:**
Foram incluídas as *interfaces* `Lead`, `Conversation` e `OmnichannelMessage` contendo todas as chaves e tipagens (opcionais quando necessário) retornadas pelo backend, de acordo com o `BaseModel` em `crm.py`. Os `any` soltos foram substituídos por genéricos fortemente tipados como `useState<Lead[]>([])` e `(l: Lead)`.

### 2. Endpoints Órfãos e Resíduos de Funcionalidades Deletadas (`src/services/api.ts`)
**Descrição:**
Uma funcionalidade relacionada ao scrapper (`ScrapperView.tsx`) que possuía requisições próprias, foi removida do sidebar e do roteador. No entanto, o tratamento do arquivo solto e das condições dinâmicas de erro para essa funcionalidade ainda permaneciam na lógica fundamental do `src/services/api.ts`, interceptando respostas do tipo 401 usando `url.includes('/scrapper/')`.
**Ação Tomada:**
O arquivo não consumido `src/pages/ScrapperView.tsx` foi permanentemente deletado. A condição de interceptação customizada dentro do tratamento de re-autenticação foi purgada do `api.ts`, limpando completamente a referência ao endpoint inexistente e órfão.

## Conclusões
- A arquitetura dos *endpoints* no frontend (`/api/v1/crm`, `/api/v1/whatsapp`, `/api/v1/projects`, etc) foi auditada e está consumindo adequadamente as rotas criadas no FastAPI (`@router.get`, `@router.post`).
- Os *Webhooks* dinâmicos (`/webhooks/events/crm-chats`) também têm suas URIs formatadas corretamente utilizando concatenação, alinhados à recepção pelo `FastAPI`.
- Testes E2E (Backend) e de Interface e API (Frontend - Vitest) validam que o contrato de tipagem foi garantido sem quebras em run-time.
