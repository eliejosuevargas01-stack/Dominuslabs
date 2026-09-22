# GOAL — Integração DominusLabs ↔ Open Delivery (Pedidos10 e plataformas aderentes)

## 1. Objetivo

Conectar o DominusLabs a plataformas de delivery externas (Pedidos10, iFood, aiqfome, Delivery Much, etc.) usando o padrão **Open Delivery API v1.7.x da Abrasel**, de forma **multi-tenant escalável**, sem exigir conhecimento técnico do operador/tenant.

## 2. Problema

Atualmente o DominusLabs recebe pedidos exclusivamente via agente IA (n8n → WhatsApp → Dominus AI → Order Manager). Para escalar como SaaS multi-tenant vendido por assinatura, cada loja (tenant) precisa receber pedidos de marketplaces de delivery — sem que o operador da loja precise lidar com credenciais OAuth, webhooks ou APIs.

## 3. Experiência do Tenant (UX obrigatória)

O tenant **não é desenvolvedor**. A integração deve funcionar assim:

1. Tenant abre o painel DominusLabs → Configurações → Integrações de Delivery
2. Vê uma lista de plataformas disponíveis (Pedidos10, iFood, etc.) com botão "Conectar"
3. Clica em "Conectar" → é redirecionado para a tela de login da plataforma (OAuth2 Authorization Code ou link de parceiro)
4. Autoriza o acesso → é redirecionado de volta ao DominusLabs
5. A integração está ativa. Pedidos começam a chegar no Order Manager.

**Alternativa quando a plataforma não suporta OAuth redirect**: a tela mostra um campo para "Código da loja" (fornecido pela plataforma ao lojista) e o DominusLabs faz a troca de credenciais nos bastidores.

Em **nenhum cenário** o tenant precisa lidar com clientId, clientSecret, baseURLs, webhooks ou configurações de API.

## 4. Definição de Pronto

1. Um tenant conecta sua loja ao Pedidos10 pelo painel administrativo do DominusLabs sem ação técnica.
2. Pedidos recebidos de plataformas externas chegam ao Order Manager existente em tempo real (SSE/WS, alarmes TTS, controle de status).
3. Mudanças de status no PDV (aceitar, preparar, despachar, entregar) são notificadas automaticamente à plataforma de origem.
4. O cardápio do tenant (tabela `Product` + `CompanySetting`) é exposto automaticamente no formato Open Delivery.
5. Cada tenant tem credenciais isoladas por plataforma — nenhum tenant acessa dados de outro.
6. O sistema suporta N plataformas simultâneas por tenant.
7. Encriptação existente (crypto.py, DOMINUS_PRIVATE_KEY) é reusada para proteger credenciais at-rest.

## 5. Infraestrutura existente que será reusada

| Componente | O que já faz | Como será adaptado |
|---|---|---|
| `IdentityClient` | OAuth2 M2M com cache TTL, retry, criptografia | Padrão arquitetural para o novo `PlatformTokenManager` |
| `Product` model | Cardápio por tenant (nome, preço, categoria, disponível) | Serializado para formato Open Delivery `GET /merchant` |
| `CompanySetting` model | Dados da loja (nome, CNPJ, endereço, horários, delivery) | Mapeado para Open Delivery merchant schema |
| `OrderManagerOrder` + `OrderManagerOrderItem` | Pedidos por tenant com status transitions | Recebe pedidos Open Delivery via adapter |
| `broadcast()` SSE/WS | Realtime para o PDV | Funciona sem mudanças para pedidos externos |
| `notify_order_status()` HMAC | Callback para n8n | Padrão para o novo callback Open Delivery |
| Crypto (`encrypt_payload`, `decrypt_payload`) | AES-256-GCM + RSA-OAEP | Encriptar credenciais at-rest |
| `authenticate_n8n_request()` | Validação HMAC de webhooks | Padrão para validação de webhooks Open Delivery |

## 6. Fora do Escopo

- Mudanças no fluxo n8n existente (Dominus AI, Buffer, CRM, Respostas)
- Mudanças no Order Manager frontend (Kanban, Lista, Manual já implementados)
- Logística / entregadores (módulo Logistics do Open Delivery — fase futura)
- Reconciliação financeira (módulo BETA do Open Delivery — fase futura)
- Deploy e migração de banco (requer aprovação explícita)

## 7. Restrições

- Zero dependências novas no backend sem aprovação
- Credenciais de plataformas externas encriptadas at-rest (não plaintext)
- Nenhum secret exposto em logs, frontend ou commits
- Não tocar no IdentityClient/WhatsAppClient existente — criar adapter paralelo
- Não tocar nos workflows n8n
- Multi-tenant obrigatório: tenant_id em todos os modelos, queries e validações
- Não alterar endpoints existentes — apenas adicionar novos
