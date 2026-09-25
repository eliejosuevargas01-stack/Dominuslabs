# TASKS — Integração Open Delivery Multi-Tenant

> Cada task é autocontida: contém o que implementar, onde, critérios de aceitação e testes.
> Nenhuma task deve ser executada sem aprovação explícita do usuário.

---

## FASE 1: Fundação

### TASK-OD-001: Modelo TenantPlatformIntegration

**Arquivo**: `project-hub/backend/app/models/tenant_platform_integration.py` (novo)
**O que fazer**:
- Criar model `TenantPlatformIntegration` conforme plan.md
- Adicionar campos `source_platform` e `external_order_id` ao `OrderManagerOrder`
- **Não** criar migration — apenas model; migration será task separada com aprovação

**Critérios**:
- Model importável sem erros
- Todos os campos com tipos corretos
- UniqueConstraint em (tenant_id, platform, merchant_id)
- `credentials_enc` é Text (armazena JSON encriptado)
- Nenhum campo armazena credencial em plaintext
- Tests existentes continuam passando

---

### TASK-OD-002: PlatformTokenManager service

**Arquivo**: `project-hub/backend/app/services/platform_token_manager.py` (novo)
**O que fazer**:
- Criar `PlatformTokenManager` seguindo o padrão exato do `IdentityClient`
- Cache TTL em memória por (tenant_id, platform)
- `get_token(tenant_id, platform)` → obtém ou renova token OAuth2 client_credentials
- Decripta credenciais do DB usando crypto.py
- Retry com backoff exponencial (3 tentativas)
- Fail-closed: sem credencial → HTTPException 503
- Singleton como `identity_client`

**Diferenças vs IdentityClient**:
- Não usa criptografia de payload (Open Delivery é REST simples + Bearer)
- baseURL vem do DB (TenantPlatformIntegration.base_url), não de settings
- clientId/clientSecret vêm do DB encriptado, não de env vars
- Endpoint OAuth2: `POST {auth_url}/oauth/token` com grant_type=client_credentials

**Critérios**:
- Token cacheado e reusado dentro do TTL
- Token expirado é renovado automaticamente
- Credenciais nunca aparecem em log ou exception
- Test unitário com mock httpx

---

### TASK-OD-003: OpenDeliveryAdapter — Inbound (receber pedidos)

**Arquivo**: `project-hub/backend/app/services/open_delivery_adapter.py` (novo)
**Endpoints**: 
- `POST /api/v1/od/{platform}/orderUpdate` — webhook recebido da plataforma
- `GET /api/v1/od/{platform}/events:polling` — polling alternativo
- `POST /api/v1/od/{platform}/events/acknowledgment` — confirma recebimento

**O que fazer**:
- Router em `project-hub/backend/app/api/endpoints/open_delivery.py` (novo)
- Registrar no app FastAPI
- Validar token/assinatura do webhook (Bearer token da plataforma)
- Identificar tenant pelo `merchant_id` do header ou body → lookup em TenantPlatformIntegration
- Converter payload Open Delivery para formato `OrderManagerOrder`
- Persistir com `source_platform` e `external_order_id`
- Chamar `broadcast("new_order", ...)` existente
- Retornar 200 com acknowledgment

**Mapeamento**: conforme tabela "Pedido (inbound)" no plan.md

**Critérios**:
- Pedido da plataforma chega ao Order Manager com todos os campos mapeados
- SSE/WS broadcast funciona
- tenant_id correto (isolamento)
- Pedido duplicado (mesmo external_order_id) faz update, não duplicata
- Webhook sem token válido → 401
- Webhook com merchant_id desconhecido → 404
- Tests existentes continuam passando

---

### TASK-OD-004: Encriptação de credenciais at-rest

**Arquivo**: `project-hub/backend/app/core/credential_vault.py` (novo)
**O que fazer**:
- `encrypt_credentials(data: dict) → str` — encripta JSON com AES-256-GCM + DOMINUS_PRIVATE_KEY derivada
- `decrypt_credentials(enc: str) → dict` — decripta
- Usar primitivas existentes do crypto.py, adaptadas para dados estáticos at-rest
- Não usar a mesma chave AES que mensagens em trânsito — derivar key material separado

**Critérios**:
- Round-trip: decrypt(encrypt(data)) == data
- Sem DOMINUS_PRIVATE_KEY → fail-closed
- Credencial encriptada não é decodificável sem a chave
- Test unitário com dados de exemplo

---

## FASE 2: Status Sync Outbound

### TASK-OD-005: Propagação de status para plataforma de origem

**Arquivo**: modificar `project-hub/backend/app/api/endpoints/orders.py`
**O que fazer**:
- Nos endpoints `accept_order`, `update_order_status`: após persistir e broadcast, verificar se o pedido tem `source_platform`
- Se sim, usar PlatformTokenManager para obter token + OpenDeliveryAdapter para enviar o status
- Mapeamento: conforme tabela "Status (outbound)" no plan.md
- Background task (como o webhook n8n existente) com retry

**Critérios**:
- Pedido interno (source_platform=None) → comportamento idêntico ao atual (n8n callback)
- Pedido externo (source_platform="pedidos10") → callback para a plataforma via Open Delivery
- Falha no callback externo não impede o operador de usar o PDV
- Retry com backoff
- Tests existentes continuam passando

---

## FASE 3: Cardápio / Merchant Export

### TASK-OD-006: MerchantExporter service

**Arquivo**: `project-hub/backend/app/services/merchant_exporter.py` (novo)
**Endpoint**: `GET /api/v1/od/{platform}/merchant` (autenticado pela plataforma)
**O que fazer**:
- Ler `CompanySetting` do tenant → montar dados gerais do merchant
- Ler `Product` do tenant → montar itens/categorias
- Serializar para schema Open Delivery v1.7.x
- Endpoint autenticado pelo token da plataforma (Bearer)

**Mapeamento**: conforme tabela "Cardápio (outbound)" no plan.md

**Critérios**:
- Resposta válida no schema Open Delivery
- Produtos indisponíveis marcados como UNAVAILABLE
- Categorias derivadas de Product.categoria
- Sem dados de outro tenant
- Test unitário com fixture de produtos

---

## FASE 4: Admin UI

### TASK-OD-007: Tela de Integrações de Delivery (frontend)

**Arquivo**: `src/pages/IntegrationsView.tsx` (novo) + rota em `App.tsx` + link em `Sidebar.tsx`
**O que fazer**:
- Página "Integrações de Delivery" acessível pelo menu lateral
- Lista de plataformas disponíveis com logo, nome, status (conectado/desconectado)
- Botão "Conectar" → modal com campo "Código da loja" (ou redirect OAuth quando disponível)
- Botão "Desconectar" com confirmação
- Toggle ativar/desativar integração
- Indicador de última sincronização e último erro

**Backend endpoints necessários** (criar junto):
- `GET /api/v1/integrations` — lista integrações do tenant
- `POST /api/v1/integrations` — cria integração (recebe platform + store_code)
- `DELETE /api/v1/integrations/{id}` — remove integração
- `PATCH /api/v1/integrations/{id}` — ativar/desativar

**Critérios**:
- Tenant vê apenas suas integrações
- Conectar com código da loja funciona
- Desconectar remove credenciais
- Toggle funciona
- TypeScript compila sem erros
- Nenhuma credencial visível no frontend

---

### TASK-OD-008: Backend de gerenciamento de integrações

**Arquivo**: `project-hub/backend/app/api/endpoints/integrations.py` (novo)
**O que fazer**:
- CRUD endpoints para TenantPlatformIntegration
- Auth via get_operator_tenant_id (JWT)
- POST recebe platform + store_code → DominusLabs troca por credenciais com a plataforma → encripta → salva
- DELETE faz soft-delete (is_active=False) e limpa credenciais
- GET nunca retorna credenciais — apenas metadata

**Critérios**:
- Credenciais nunca retornadas ao frontend
- tenant_id sempre filtrado pelo JWT
- Validação de platform (whitelist)
- Test com mock de troca de credenciais

---

## FASE 5: Homologação

### TASK-OD-009: Testes no sandbox Open Delivery

**O que fazer**:
- Registrar no sandbox (developer.opendelivery.com.br)
- Testar fluxo completo: onboarding → receber pedido → confirmar → entregar
- Validar schemas com ferramenta oficial (Open Delivery Schema Validator)
- Documentar incompatibilidades encontradas

**Critérios**:
- Pedido sandbox chega ao Order Manager local
- Status sync funciona ida e volta
- Cardápio é lido corretamente pela plataforma sandbox

---

### TASK-OD-010: Homologação Pedidos10

**O que fazer**:
- Contato com dev@dev10.com.br (equipe Dev10/Pedidos10)
- Solicitar credenciais de homologação
- Testar com loja real em ambiente de staging
- Documentar ajustes específicos do Pedidos10

**Critérios**:
- Pedido real do app Pedidos10 chega ao Order Manager
- Status atualizado no Pedidos10 quando operador aceita no PDV
- Cardápio visível no app Pedidos10

---

## Prioridade e dependências

```
TASK-OD-001 (model) ──┐
                       ├──▶ TASK-OD-003 (inbound) ──▶ TASK-OD-005 (status sync)
TASK-OD-004 (vault) ──┤
                       ├──▶ TASK-OD-002 (token mgr)
                       │
                       └──▶ TASK-OD-006 (merchant) ──▶ TASK-OD-009 (sandbox)
                                                              │
TASK-OD-008 (backend)─▶ TASK-OD-007 (UI) ───────────────────┘
                                                              │
                                                              └──▶ TASK-OD-010 (homologação)
```
