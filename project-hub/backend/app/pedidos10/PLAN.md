# PLAN — Pedidos10 Bridge — Passos de Implementação

## Estrutura de Arquivos a Criar
```
app/pedidos10/
├── __init__.py                  # Exporta: Pedidos10Bridge, pedidos10_manager
├── constants.py                 # Constantes da API (tokens fixos, URLs, versões)
├── auth_manager.py              # Login httpx + reauth automático no 401
├── config_manager.py            # Busca + decripta config-env (AES-ECB)
├── catalog_client.py            # Busca catálogo de produtos
├── orders_client.py             # Busca pedidos (polling de fallback)
├── mqtt_client.py               # AWS IoT Core MQTT over WebSocket + SigV4
├── event_dispatcher.py          # Despacha eventos recebidos do MQTT
├── bridge.py                    # Orquestra todos os componentes
├── manager.py                   # Singleton global: Pedidos10Manager (multi-tenant)
├── schemas.py                   # Pydantic: PedidosEvent, CatalogItem, etc.
├── router.py                    # FastAPI router: /pedidos10/* (connect, status, catalog)
└── cli.py                       # CLI de diagnóstico e smoke test
```

## Passos de Implementação

### PASSO 1 — `constants.py`
Definir todas as constantes da API Pedidos10 descobertas via engenharia reversa:
- `BASE_URL`, `TOKEN_SERVER`, `APP_NAME`, `ID_ORIGEM`, `NUM_VERSAO`, `DES_VERSAO`
- `AES_ECB_KEY` (chave para decriptar config-env — `YL` do JS)
- Headers padrão de navegador para evitar bloqueios

### PASSO 2 — `schemas.py`
Pydantic models para:
- `Pedidos10Credentials` (email, password — nunca serializado em log)
- `Pedidos10Session` (jwt, token_u, estabelecimento_id, channel_websocket)
- `MqttConfig` (region, endpoint, key_id, secret_key)
- `PedidosEvent` (ind_evento, payload dict)
- `CatalogItem`, `OrderItem`

### PASSO 3 — `auth_manager.py`
```python
class AuthManager:
    async def login(email, password) -> Pedidos10Session
        # POST /auth com payload Az() completo
        # Retorna jwt + token_u
        # On 400 → raise InvalidCredentialsError
    
    async def get_user_info(session) -> dict
        # GET /usuario/{qt()} 
        # Retorna merchants[] com des_channel_websocket
    
    async def get_session(integration_db_record) -> Pedidos10Session
        # 1. decrypt_credentials(integration.credentials_enc)
        # 2. Verifica cache em memória (TTL 23h)
        # 3. Se expirado → login() → atualiza cache
        # Reauth automático: expõe refresh() chamado no 401
    
    async def refresh(integration_id) -> Pedidos10Session
        # Força novo login, invalida cache
```
**Segurança**: senha nunca aparece em logs — usar `***` nos handlers de exceção.

### PASSO 4 — `config_manager.py`
```python
class ConfigManager:
    def _decrypt_aes_ecb(ciphertext_b64: str) -> dict
        # Usa cryptography.hazmat AES-ECB + PKCS7
        # Chave: AES_ECB_KEY do constants.py (derivada do JS)
        # Retorna dict com mqtt_region, mqtt_endpoint, mqtt_key_id, mqtt_secret_key
    
    async def get_mqtt_config(session) -> MqttConfig
        # GET /config-env/{qt()}
        # Decripta resposta
        # Cache longo (24h) — raramente muda
        # Fallback: se decriptação falhar → MqttConfig vazia → usar polling
```

### PASSO 5 — `mqtt_client.py`
```python
class MqttClient:
    def _build_presigned_url(config: MqttConfig) -> str
        # Reproduz função le() do JS do Pedidos10
        # SigV4: HMAC-SHA256, canonical request, presigned WSS URL
        # wss://{endpoint}/mqtt?X-Amz-Algorithm=...&X-Amz-Signature=...
        # URL válida apenas no momento da conexão (usa datetime.utcnow())
    
    async def connect(config: MqttConfig, channels: list[str], on_message: Callable)
        # websockets.connect(presigned_url, subprotocols=["mqtt"])
        # Handshake MQTT CONNECT packet (protocolo MQTT 3.1.1 over WS)
        # SUBSCRIBE em cada channel de des_channel_websocket
        # Loop de recebimento com parse de MQTT frames
    
    async def _reconnect_loop()
        # Reconexão com backoff: 3s → 6s → 12s → max 60s
        # Após 401/403 MQTT → chama auth_manager.refresh() antes de reconectar
        # Max 60 tentativas antes de marcar como FAILED e notificar
    
    async def disconnect()
        # MQTT DISCONNECT packet + fechar websocket
```
**Implementação do protocolo MQTT manual** (sem lib externa além de `websockets`):
- CONNECT packet com clientId único (`{timestamp}_{random}`)
- SUBSCRIBE packet para cada tópico
- PINGREQ a cada 30s para keepalive
- Parse de PUBLISH packets recebidos

### PASSO 6 — `event_dispatcher.py`
```python
class EventDispatcher:
    def __init__(self, tenant_id: str, callbacks: dict)
    
    async def dispatch(raw_message: str)
        # Parse JSON do payload MQTT
        # Switch por ind_evento:
        #   "pedido"                   → on_order(event)
        #   "mensagem"                 → on_message(event)
        #   "fechamento-estabelecimento" → on_store_close(event)
        #   "impressao"                → ignorar (log apenas)
        #   default                    → log warning
    
    # Callbacks registráveis:
    # on_order, on_message, on_store_close, on_unknown
```

### PASSO 7 — `orders_client.py`
```python
class OrdersClient:
    async def get_pending_orders(session, merchant_id) -> list[OrderItem]
        # GET /lista-pedidos-aguardando-confirmacao/{qt()}
    
    async def get_orders(session, merchant_id) -> list[OrderItem]
        # GET /lista-pedidos/{qt()}
    
    # Usado como fallback se MQTT não conectar
```

### PASSO 8 — `catalog_client.py`
```python
class CatalogClient:
    async def get_catalog(session, merchant_id) -> list[CatalogItem]
        # GET /estabelecimento-cardapio/{qt()}
        # Retorna lista de produtos com preço, categoria, status
    
    async def sync_to_dominus(session, merchant_id, db) -> dict
        # Futuro: mapear catálogo Pedidos10 → produtos DominusLabs
        # Por ora apenas retorna os dados brutos
```

### PASSO 9 — `bridge.py`
```python
class Pedidos10Bridge:
    """
    Ciclo de vida de uma conexão ativa para um tenant+integration.
    Orquestra: AuthManager → ConfigManager → MqttClient → EventDispatcher
    """
    
    async def start(integration_db_record)
        # 1. AuthManager.get_session() → session
        # 2. AuthManager.get_user_info() → merchants + channels
        # 3. ConfigManager.get_mqtt_config() → MqttConfig
        # 4. MqttClient.connect(config, channels, on_message=dispatcher.dispatch)
        # 5. Inicia reconnect_loop em background task
        # 6. Status → CONNECTED
    
    async def stop()
        # MqttClient.disconnect()
        # Cancela background tasks
        # Status → STOPPED
    
    async def _handle_401()
        # AuthManager.refresh()
        # ConfigManager.invalidate_cache()
        # MqttClient.reconnect()
    
    @property
    def status() -> Literal["CONNECTING", "CONNECTED", "RECONNECTING", "FAILED", "STOPPED"]
```

### PASSO 10 — `manager.py`
```python
class Pedidos10Manager:
    """
    Singleton global. Gerencia múltiplos bridges (um por integration ativa).
    Chave: integration.id (UUID)
    """
    
    async def start_integration(integration_id, db)
        # Busca TenantPlatformIntegration no DB
        # Cria Pedidos10Bridge e chama bridge.start()
        # Registra em _bridges dict
    
    async def stop_integration(integration_id)
        # bridge.stop() + remove do dict
    
    async def restart_integration(integration_id, db)
        # stop + start
    
    def get_status(integration_id) -> dict
        # Retorna status, uptime, last_event_at, error
    
    def get_all_statuses() -> list[dict]
        # Retorna status de todas as bridges ativas
    
    async def on_order_received(tenant_id, event: PedidosEvent)
        # Ponto de integração com DominusLabs
        # Por ora: log + emit SSE (futuro: chamar n8n webhook)

# Singleton
pedidos10_manager = Pedidos10Manager()
```

### PASSO 11 — `router.py`
```python
# FastAPI APIRouter com prefix="/pedidos10", tags=["Pedidos10"]
# TODOS os endpoints exigem autenticação DominusLabs (Bearer JWT)

POST   /connect              # Registra credenciais + inicia bridge
DELETE /disconnect/{id}      # Para bridge e remove integração
GET    /status               # Lista status de todas as bridges do tenant
GET    /status/{id}          # Status específico de uma integration
POST   /refresh/{id}         # Força reauth manual
GET    /catalog/{id}         # Busca catálogo atual da loja
GET    /orders/{id}          # Busca pedidos atuais (fallback REST)
POST   /test-connection      # Testa credenciais sem persistir
```

### PASSO 12 — `cli.py`
```python
# python -m app.pedidos10.cli <comando>
# Comandos:
#   smoke-test --email X --password Y   → testa login + config-env + MQTT
#   decrypt-config --b64 <data>          → testa decriptação AES-ECB
#   test-mqtt --region X --endpoint Y    → testa conexão MQTT isolada
```

### PASSO 13 — `__init__.py`
Exportar os símbolos públicos:
```python
from .bridge import Pedidos10Bridge
from .manager import pedidos10_manager
from .router import router as pedidos10_router
from .schemas import PedidosEvent, CatalogItem, OrderItem
```

## Ordem de Execução do Worker

1. `constants.py` + `schemas.py` (sem dependências)
2. `auth_manager.py` (depende de constants, credential_vault existente)
3. `config_manager.py` (depende de auth_manager, constants)
4. `mqtt_client.py` (depende de config_manager)
5. `event_dispatcher.py` (independente)
6. `orders_client.py` + `catalog_client.py` (dependem de auth_manager)
7. `bridge.py` (orquestra tudo)
8. `manager.py` (singleton de bridge)
9. `router.py` (depende de manager)
10. `cli.py` (depende de tudo)
11. `__init__.py` (exports finais)

## Testes de Aceitação

### T1 — Login e reauth
```bash
# Deve retornar session com jwt e token_u
python -m app.pedidos10.cli smoke-test --email $EMAIL --password $PASS
```

### T2 — Decriptação config-env
```bash
# Deve retornar mqtt_region, mqtt_endpoint, mqtt_key_id, mqtt_secret_key
python -m app.pedidos10.cli decrypt-config --b64 "svafzmL9z61m..."
```

### T3 — Conexão MQTT
```bash
# Deve conectar, subscrever e receber PINGRESP em 10s
python -m app.pedidos10.cli test-mqtt
```

### T4 — Reauth automático
```bash
# Simular 401: apagar JWT do cache → bridge deve se reconectar automaticamente
# Verificado via status: RECONNECTING → CONNECTED
```

### T5 — Isolamento
```bash
# Verificar que NENHUM arquivo existente foi modificado
git -C /home/eliezer/Escritorio/dominuslabs/project-hub diff --name-only HEAD
# Saída esperada: VAZIA (só novos arquivos em app/pedidos10/)
```

## Contratos de Integração Futura (NÃO implementar agora)

Quando o Captain aprovar a integração no backend existente, estes são os únicos pontos de toque:
1. `app/main.py` linha 181: adicionar `app.include_router(pedidos10_router, prefix=settings.API_V1_STR)`
2. `app/main.py` startup: adicionar `await pedidos10_manager.start_all_active(db)` no lifespan
3. `app/models/__init__.py`: nenhuma alteração necessária (usa TenantPlatformIntegration existente)

## Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| AES-ECB key do config-env mudar | Fallback automático para polling 60s |
| JWT Pedidos10 expirar abruptamente | Reauth no 401, max 3 tentativas antes de FAILED |
| AWS IoT endpoint mudar | Recarrega config-env a cada reconnect |
| Pedidos10 bloquear por User-Agent | Headers realistas de navegador Chrome em todas as requests |
| Tópico MQTT por merchant mudar | Rebusca `/usuario` a cada reconnect |
