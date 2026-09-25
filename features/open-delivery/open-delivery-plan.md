# PLAN — Integração Open Delivery Multi-Tenant

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│                     DominusLabs Backend                           │
│                                                                    │
│  ┌─────────────────────────────────────┐                          │
│  │  TenantPlatformIntegration (model)  │  Credenciais encriptadas │
│  │  tenant_id + platform → credentials │  por tenant/plataforma   │
│  └─────────────┬───────────────────────┘                          │
│                │                                                   │
│  ┌─────────────▼───────────────────────┐                          │
│  │  PlatformTokenManager (service)     │  OAuth2 client_credentials│
│  │  Cache TTL por tenant+plataforma    │  seguindo padrão do      │
│  │  Retry + refresh automático         │  IdentityClient existente│
│  └─────────────┬───────────────────────┘                          │
│                │                                                   │
│  ┌─────────────▼───────────────────────┐  ┌─────────────────────┐│
│  │  OpenDeliveryAdapter (service)      │  │  MerchantExporter    ││
│  │                                      │  │  (service)           ││
│  │  Inbound:                            │  │                      ││
│  │  POST /v1/od/orderUpdate (webhook) ──┼──▶ Product + Company   ││
│  │  GET  /v1/od/events:polling         │  │  → Open Delivery     ││
│  │  POST /v1/od/events/acknowledgment  │  │  merchant schema     ││
│  │                                      │  └─────────────────────┘│
│  │  Outbound (status sync):            │                          │
│  │  POST /orders/{id}/confirm          │                          │
│  │  POST /orders/{id}/preparing        │                          │
│  │  POST /orders/{id}/readyForPickup   │                          │
│  │  POST /orders/{id}/dispatch         │                          │
│  │  POST /orders/{id}/delivered        │                          │
│  │  POST /orders/{id}/requestCancel    │                          │
│  └─────────────┬───────────────────────┘                          │
│                │                                                   │
│  ┌─────────────▼───────────────────────┐                          │
│  │  Order Manager (existente)          │                          │
│  │  receive_order() → broadcast()      │                          │
│  │  SSE/WS → PDV do operador           │                          │
│  └─────────────────────────────────────┘                          │
│                                                                    │
│  ┌─────────────────────────────────────┐                          │
│  │  Admin UI: Integrações de Delivery  │                          │
│  │  "Conectar" → OAuth/Código loja     │                          │
│  │  Lista de integrações ativas        │                          │
│  │  Ativar/desativar por plataforma    │                          │
│  └─────────────────────────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
         ▲                           │
         │ OAuth2 + Open Delivery    │ Webhooks (orderUpdate)
         │ (por tenant+plataforma)   │ Status callbacks
         ▼                           ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Pedidos10   │ │  iFood       │ │  aiqfome     │
│  (Ordering   │ │  (Ordering   │ │  (Ordering   │
│   App)       │ │   App)       │ │   App)       │
└──────────────┘ └──────────────┘ └──────────────┘
```

## Fluxo: Tenant conecta plataforma

```
Tenant (Painel Admin)              DominusLabs                    Pedidos10
      │                                │                              │
      │  1. Clica "Conectar Pedidos10" │                              │
      │──────────────────────────────▶│                              │
      │                                │  2. Redirect OAuth ou        │
      │                                │     pede "Código da loja"    │
      │  3. Autoriza / insere código  │                              │
      │──────────────────────────────▶│                              │
      │                                │  4. Troca código por         │
      │                                │     clientId + clientSecret  │
      │                                │─────────────────────────────▶│
      │                                │  5. Recebe credenciais       │
      │                                │◀─────────────────────────────│
      │                                │  6. Encripta + salva em      │
      │                                │     TenantPlatformIntegration│
      │                                │  7. Obtém token OAuth2       │
      │                                │─────────────────────────────▶│
      │                                │  8. Registra merchantOnboard │
      │                                │─────────────────────────────▶│
      │  9. "Integração ativa ✅"      │                              │
      │◀──────────────────────────────│                              │
```

## Fluxo: Pedido recebido de plataforma externa

```
Pedidos10                    DominusLabs                         PDV (Operador)
    │                            │                                    │
    │ 1. POST /v1/od/orderUpdate │                                    │
    │───────────────────────────▶│                                    │
    │                            │ 2. Valida assinatura/token         │
    │                            │ 3. Identifica tenant por merchantId│
    │                            │ 4. Converte para formato interno   │
    │                            │ 5. Persiste OrderManagerOrder      │
    │                            │ 6. broadcast("new_order")          │
    │                            │───────────────────────────────────▶│
    │                            │                                    │ 7. Alarme TTS
    │                            │                                    │ 8. Operador aceita
    │                            │◀───────────────────────────────────│
    │                            │ 9. POST /orders/{id}/confirm       │
    │◀───────────────────────────│                                    │
    │                            │                                    │
```

## Modelo de dados

### TenantPlatformIntegration (novo)

```python
class TenantPlatformIntegration(Base):
    __tablename__ = "tenant_platform_integrations"
    
    id              = Column(UUID, primary_key=True, default=uuid4)
    tenant_id       = Column(String(255), nullable=False, index=True)
    platform        = Column(String(64), nullable=False)         # "pedidos10", "ifood"
    display_name    = Column(String(255), nullable=True)         # "Pedidos10 - Loja Centro"
    
    # Credenciais (encriptadas at-rest com DOMINUS_PRIVATE_KEY via crypto.py)
    credentials_enc = Column(Text, nullable=False)               # JSON encriptado: {clientId, clientSecret, ...}
    
    # Referências da plataforma
    app_id          = Column(String(255), nullable=True)         # AppId da Ordering Application
    merchant_id     = Column(String(255), nullable=True)         # ID do merchant na plataforma
    base_url        = Column(String(512), nullable=False)        # baseURL da API da plataforma
    auth_url        = Column(String(512), nullable=True)         # baseURL de auth (se diferente)
    webhook_secret  = Column(Text, nullable=True)                # Para validar webhooks recebidos (encriptado)
    
    # Estado
    is_active       = Column(Boolean, default=True, index=True)
    last_sync_at    = Column(DateTime, nullable=True)
    last_error      = Column(Text, nullable=True)
    
    # Onboarding simplificado
    store_code      = Column(String(255), nullable=True)         # "Código da loja" que o tenant insere
    onboarding_status = Column(String(32), default="pending")    # pending, active, error, disabled
    
    created_at      = Column(DateTime, default=utc_now)
    updated_at      = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "platform", "merchant_id", 
                        name="uq_tenant_platform_merchant"),
    )
```

### OrderManagerOrder (alteração)

```python
# Adicionar campo para rastrear origem do pedido:
source_platform  = Column(String(64), nullable=True, default=None)  # None=n8n, "pedidos10", "ifood"
external_order_id = Column(String(255), nullable=True, index=True)  # ID do pedido na plataforma externa
```

## Mapeamento Open Delivery ↔ DominusLabs

### Pedido (inbound: Open Delivery → Order Manager)

| Open Delivery | DominusLabs |
|---|---|
| `order.id` | `external_order_id` |
| `order.type` (DELIVERY/TAKEOUT) | `tipo_entrega` |
| `order.customer.name` | `customer_name` |
| `order.delivery.deliveryAddress` | `address` |
| `order.total.orderAmount` | `total` |
| `order.items[].name` | `OrderManagerOrderItem.nome` |
| `order.items[].quantity` | `OrderManagerOrderItem.quantidade` |
| `order.items[].unitPrice` | `OrderManagerOrderItem.preco_unitario` |
| `order.items[].totalPrice` | `OrderManagerOrderItem.subtotal` |
| `order.items[].externalCode` | `OrderManagerOrderItem.codigo` |
| `order.items[].observations` | `OrderManagerOrderItem.observacoes` |

### Status (outbound: Order Manager → Open Delivery)

| Order Manager | Open Delivery endpoint |
|---|---|
| `pending → accepted` | `POST /orders/{id}/confirm` |
| `accepted → preparing` | `POST /orders/{id}/preparing` |
| `preparing → ready_for_delivery` | `POST /orders/{id}/readyForPickup` |
| `ready_for_delivery → out_for_delivery` | `POST /orders/{id}/dispatch` |
| `out_for_delivery → delivered` | `POST /orders/{id}/delivered` |
| `pending → rejected` | `POST /orders/{id}/requestCancellation` |

### Cardápio (outbound: DominusLabs → Open Delivery)

| DominusLabs | Open Delivery |
|---|---|
| `Product.nome` | `item.name` |
| `Product.preco` | `item.price.value` |
| `Product.descricao` | `item.description` |
| `Product.categoria` | `category.name` |
| `Product.disponivel` | `item.status` (AVAILABLE/UNAVAILABLE) |
| `Product.codigo_slug` | `item.externalCode` |
| `Product.imagem_url` | `item.image` |
| `CompanySetting.company_name` | `merchant.name` |
| `CompanySetting.address*` | `merchant.address` |
| `CompanySetting.business_hours` | `merchant.hours` |
| `CompanySetting.cnpj_cpf` | `merchant.document` |

## Fases de implementação

### Fase 1: Fundação (modelo + adapter + token manager)
- TenantPlatformIntegration model
- PlatformTokenManager service (baseado no IdentityClient)
- OpenDeliveryAdapter service (inbound: pedidos)
- Endpoints webhook receiver

### Fase 2: Status sync outbound
- Hook no update_order_status para propagar via adapter
- Mapeamento de status transitions

### Fase 3: Merchant/cardápio export
- MerchantExporter service
- GET /v1/od/merchant endpoint
- Serialização Product + CompanySetting → Open Delivery schema

### Fase 4: Admin UI de integração
- Tela "Integrações de Delivery" no painel
- Fluxo "Conectar" (OAuth redirect ou código da loja)
- Lista de integrações ativas com toggle

### Fase 5: Homologação
- Testes no sandbox Open Delivery (developer.opendelivery.com.br)
- Homologação com Pedidos10
- Testes E2E com pedidos reais
