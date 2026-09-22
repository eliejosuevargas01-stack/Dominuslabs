# 📊 RELATÓRIO DE INVESTIGAÇÃO - PEDIDOS10 BRIDGE (ESTILO BAILEYS)

> **Objetivo**: Validar integração temporária com Pedidos10 enquanto homologação oficial não está disponível, seguindo o padrão arquitetural do **Baileys** (WhatsApp Web library)

---

## 1. O QUE É O BAILEYS?

### 1.1 Visão Geral

**Baileys** é uma biblioteca TypeScript/JavaScript que interage com a **WhatsApp Web API** diretamente via **WebSocket**, **SEM navegador, SEM Selenium, SEM Chromium**.

**Principais características:**
- Conecta diretamente aos servidores WhatsApp via WebSocket
- Implementa protocolo **Noise + Protobuf** (criptografia)
- Autentica como dispositivo secundário (linked device)
- Persiste sessão em arquivos JSON
- EventEmitter-based, assíncrono
- 100% em Node.js (sem browser overhead)

### 1.2 Arquitetura do Baileys

```
┌─────────────────────────────────────────────────┐
│         Seu Aplicativo Node.js                   │
│                                                  │
│  ┌────────────────────────────────────────────┐│
│  │  makeWASocket()                             ││
│  │  - EventEmitter para mensagens             ││
│  │  - send/receive messages                   ││
│  │  - group management                        ││
│  └────────────────┬───────────────────────────┘│
│                   │                              │
│  ┌────────────────▼───────────────────────────┐│
│  │  Authentication State (useMultiFileAuthState)│
│  │  ├── creds.json (identidade + keys)       ││
│  │  ├── pre-key-*.json                       ││
│  │  ├── session-*.json                       ││
│  │  └── app-state-sync-key-*.json            ││
│  └────────────────┬───────────────────────────┘│
│                   │                              │
│  ┌────────────────▼───────────────────────────┐│
│  │  WebSocket Connection (Noise Protocol)     ││
│  │  - Criptografia end-to-end (Signal)        ││
│  │  - Binary frames (protobuf)                ││
│  └────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
                   │
                   ▼
        ┌────────────────────┐
        │  WhatsApp Servers  │
        │  (web.whatsapp.com)│
        └────────────────────┘
```

### 1.3 Fluxo de Autenticação Baileys

```javascript
// 1. Criar/auth state persistent
const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys')

// 2. Criar socket
const sock = makeWASocket({ auth: state })

// 3. Capturar QR Code (primeira vez)
sock.ev.on('connection.update', ({ qr }) => {
    if (qr) {
        // Exibir QR para scan manual
        qrcode.generate(qr, { small: true })
    }
})

// 4. Persistir credenciais automaticamente
sock.ev.on('creds.update', saveCreds)

// 5. Receber mensagens
sock.ev.on('messages.upsert', ({ messages }) => {
    // Processar mensagens
})

// 6. Reconexão automática
sock.ev.on('connection.update', ({ connection, lastDisconnect }) => {
    if (connection === 'close') {
        const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut
        if (shouldReconnect) {
            connectToWhatsApp() // Reconectar
        }
    }
})
```

### 1.4 Estrutura de Arquivos Persistida

```
auth_info_baileys/
├── creds.json              # Credenciais principais (identity keys, registration ID)
├── pre-key-1.json         # Pre-keys Signal protocol
├── pre-key-2.json
├── session-abc123.json    # Sessões Signal
├── session-def456.json
├── app-state-sync-key-*.json  # App state sync keys
└── sender-key-*.json      # Sender keys para grupos
```

### 1.5 Conceitos Chave

| Conceito | Descrição |
|----------|-----------|
| **Authentication State** | Objeto com creds + keys persistido |
| **creds.json** | Identidade do dispositivo, registration ID, identity keys |
| **Signal Keys** | Pre-keys, sessions, sender-keys (criptografia E2E) |
| **creds.update event** | Dispara quando credenciais mudam (requer save) |
| **Multi-file auth** | Múltiplos arquivos JSON (eficiente I/O) |
| **login uma vez** | Scan QR uma vez, depois reconecta automaticamente |

---

## 2. COMO ADAPTAR PARA PEDIDOS10?

### 2.1 Comparação: WhatsApp Web vs Pedidos10

| Aspecto | WhatsApp Web | Pedidos10 |
|---------|--------------|-----------|
| **Protocolo** | WebSocket + Noise + Protobuf | HTTP REST + possivelmente WebSocket/SSE |
| **Autenticação** | QR Code + device pairing | Login/acesso autorizado |
| **Persistent State** | Cookies + localStorage + criptografia | Cookies + localStorage + session tokens |
| **Monitor/Monitor** | web.whatsapp.com | monitor.pedidos10.com.br (ou similar) |
| **Nova mensagem** | WebSocket push em tempo real | Possível: WebSocket / SSE / polling |

### 2.2 Estratégia "Baileys para Pedidos10"

**Não podemos fazer engenharia reversa do protocolo** (como o Baileys faz), pois:
1. WhatsApp Web é documentado publicamente (projetos open-source)
2. Pedidos10 **não tem documentação pública** do protocolo interno
3. Não temos acesso ao código backend do Pedidos10

**MAS podemos fazer OBSERVAÇÃO do frontend legítimo:**

```
┌─────────────────────────────────────────────────┐
│   PEDIDOS10 BRIDGE (Playwright Approach)       │
│                                                  │
│  ┌────────────────────────────────────────────┐│
│  │  Ped10SessionManager                       ││
│  │  - Abrir Chromium com perfil persistente   ││
│  │  - Login manual único                      ││
│  │  - Monitorar status da sessão             ││
│  │  - Extrair cookies/tokens                  ││
│  └────────────────┬───────────────────────────┘│
│                   │                              │
│  ┌────────────────▼───────────────────────────┐│
│  │  Network Observer (Playwright)             ││
│  │  - page.on('request') → capturar XHR      ││
│  │  - page.on('response') → capturar JSON    ││
│  │  - Monitorar WebSocket frames              ││
│  │  - Detectar padrões de endpoints           ││
│  └────────────────┬───────────────────────────┘│
│                   │                              │
│  ┌────────────────▼───────────────────────────┐│
│  │  Protocol Discovery                        ││
│  │  - Identificar fetch/XHR/websocket/SSE    ││
│  │  - Classificar mecanismo de push           ││
│  │  - Extrair URLs, methods, headers          ││
│  │  - Validar payloads de entrada/saída      ││
│  └────────────────┬───────────────────────────┘│
│                   │                              │
│  ┌────────────────▼───────────────────────────┐│
│  │  Session Persistence                       ││
│  │  ├── storage_state.json (cookies + LS)     ││
│  │  ├── browser-profile/ (diretório Chrome)   ││
│  │  └── pedidos10_session.json (tokens)       ││
│  └────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
                   │
                   ▼
        ┌────────────────────┐
        │  Pedidos10 Backend │
        │  (API interna)     │
        └────────────────────┘
```

---

## 3. PLAYWRIGHT: INTERCEPTAÇÃO DE REDE

### 3.1 Capturar Fetch/XHR/WebSocket

**Playwright Python** permite interceptar **TODAS** as requisições de rede:

```python
from playwright.sync_api import sync_playwright
import json

def observe_pedidos10():
    captured_requests = []
    
    with sync_playwright() as p:
        # 1. Lançar com perfil persistente
        context = p.chromium.launch_persistent_context(
            user_data_dir='./pedidos10-profile',
            headless=False  # Headful para login manual
        )
        
        page = context.new_page()
        
        # 2. Intercept REQUEST
        page.on('request', lambda req: captured_requests.append({
            'method': req.method,
            'url': req.url,
            'headers': req.headers,
            'post_data': req.post_data,
            'resource_type': req.resource_type,
            'timestamp': datetime.now().isoformat()
        }))
        
        # 3. Intercept RESPONSE
        page.on('response', lambda res: captured_requests.append({
            'url': res.url,
            'status': res.status,
            'headers': res.headers,
            'body': res.text() if 'json' in res.headers.get('content-type', '') else None
        }))
        
        # 4. Navegar para o monitor
        page.goto('https://monitor.pedidos10.com.br')  # URL a descobrir
        
        # 5. Aguardar login manual
        input("Pressione Enter após fazer login...")
        
        # 6. Salvar estado da sessão
        context.storage_state(path='pedidos10-session.json')
        
        # 7. Salvar requisições capturadas
        with open('pedidos10-traffic.json', 'w') as f:
            json.dump(captured_requests, f, indent=2)
        
        context.close()
```

### 3.2 Persistent Browser Context

**Key feature**: `launch_persistent_context` salva **tudo** em disco:

```python
# Diretório do perfil persistente
user_data_dir = './pedidos10-browser-profile'

# Lança browser que mantém cookies/storage entre execuções
context = p.chromium.launch_persistent_context(
    user_data_dir=user_data_dir,
    headless=False,  # Primeira vez = headful para login
    viewport={'width': 1920, 'height': 1080}
)

# Após login, pode rodar headless
context = p.chromium.launch_persistent_context(
    user_data_dir=user_data_dir,
    headless=True  # Execuções subsequentes
)
```

**Benefícios:**
- Login manual **apenas uma vez**
- Cookies + localStorage + IndexedDB persistidos
- Pode reutilizar sessão por semanas/meses
- Igual ao `useMultiFileAuthState` do Baileys

### 3.3 storage_state() vs Persistent Context

| Método | O que faz | Persistência |
|--------|-----------|--------------|
| `storage_state()` | Salva cookies + localStorage em JSON | Explícito (manual) |
| `launch_persistent_context()` | Usa diretório de perfil completo | Automático |

**Recomendação para Pedidos10:** Usar **AMBOS**:
1. `launch_persistent_context` → Manter sessão do navegador
2. `storage_state()` → Backup/exportar sessão para requests manuais

---

## 4. DETECÇÃO DO MECANISMO DE PUSH

### 4.1 Possibilidades no Pedidos10

Baseado na arquitetura típica de delivery apps:

| Mecanismo | Probabilidade | Como detectar |
|-----------|---------------|---------------|
| **WebSocket** | 🔴 Alta | `page.on('websocket')` |
| **Server-Sent Events (SSE)** | 🟡 Média | URL com `/events` ou `/stream` |
| **HTTP Polling** | 🟡 Média | Requests periódicos GET `/orders?status=pending` |
| **Long Polling** | 🟢 Baixa | POST com timeout longo |
| **GraphQL Subscription** | 🟢 Baixa | Requer análise do payload |

### 4.2 Script de Detecção

```python
def detect_push_mechanism(page):
    """Detecta como o Pedidos10 envia novos pedidos."""
    
    websockets = []
    sse_connections = []
    poll_requests = []
    
    # WebSocket listener
    def on_websocket(ws):
        websockets.append({
            'url': ws.url,
            'opened_at': datetime.now().isoformat()
        })
        print(f"[WS] Conexão detectada: {ws.url}")
        
        ws.on('framesreceived', lambda frames: print(f"[WS] Frames recebidos: {len(frames)}"))
        ws.on('framessent', lambda frames: print(f"[WS] Frames enviados: {len(frames)}"))
    
    page.on('websocket', on_websocket)
    
    # Request listener para SSE/Polling
    def on_request(req):
        if 'event' in req.url.lower() or 'stream' in req.url.lower():
            sse_connections.append({
                'url': req.url,
                'method': req.method,
                'headers': req.headers
            })
            print(f"[SSE?] Possível SSE: {req.url}")
        
        # Detectar padrão de polling
        if 'order' in req.url.lower():
            poll_requests.append({
                'url': req.url,
                'time': datetime.now(),
                'method': req.method
            })
    
    page.on('request', on_request)
    
    # Aguardar e analisar
    page.wait_for_timeout(30000)  # 30 segundos de observação
    
    # Classificar
    if websockets:
        return 'WEBSOCKET', websockets
    elif sse_connections:
        return 'SSE', sse_connections
    elif len(poll_requests) > 5:  # Múltiplos requests = polling
        return 'POLLING', poll_requests
    else:
        return 'UNKNOWN', []
```

---

## 5. ESTRUTURA DO PEDIDOS10-BRIDGE (PYTHON)

### 5.1 Estrutura de Diretórios

```
pedidos10-bridge/
│
├── app/
│   ├── main.py                        # FastAPI entrypoint
│   │
│   ├── browser/
│   │   ├── session_manager.py         # Gerencia Chromium persistente
│   │   ├── network_observer.py        # Intercepta Fetch/XHR/WS
│   │   └── login_required.py          # Detecta sessão expirada
│   │
│   ├── pedidos10/
│   │   ├── client.py                  # HTTP client reproduzindo requests observados
│   │   ├── mapper.py                  # Pedidos10 JSON → CanonicalOrder
│   │   ├── schemas.py                 # Pydantic schemas
│   │   └── protocol.py                 # Constantes de endpoints descobertos
│   │
│   ├── domain/
│   │   ├── order.py                    # CanonicalOrder model
│   │   └── provider.py                # OrderProvider interface
│   │
│   ├── api/
│   │   ├── health.py                  # GET /health
│   │   ├── session.py                 # GET/POST /session/*
│   │   └── orders.py                  # GET /orders
│   │
│   └── config.py                      # Env vars + configuração
│
├── browser-profile/                   # Perfil Chromium persistente (gitignored)
│
├── session-backup/
│   ├── storage_state.json             # Cookies + localStorage exportados
│   └── pedidos10_tokens.json          # Tokens extraídos
│
├── docs/
│   ├── observed-api.md                # Endpoints descobertos
│   ├── traffic-analysis.md             # Análise de tráfego
│   └── integration-notes.md
│
├── scripts/
│   ├── observe-traffic.py             # Script de descoberta
│   ├── test-session.py                # Testar sessão persistida
│   └── extract-tokens.py              # Extrair tokens do browser
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### 5.2 Componente Principal: Ped10SessionManager

```python
# app/browser/session_manager.py

from playwright.sync_api import sync_playwright, BrowserContext, Page
from pathlib import Path
import json
from typing import Optional
from enum import Enum

class SessionState(Enum):
    CONNECTED = "connected"
    AUTH_REQUIRED = "auth_required"
    SESSION_EXPIRED = "session_expired"
    ERROR = "error"

class Ped10SessionManager:
    """
    Gerencia sessão autenticada do Pedidos10 usando Playwright.
    
    Similar ao useMultiFileAuthState do Baileys:
    - Persiste estado em user_data_dir
    - Detecta sessão expirada
    - Permite login manual único
    - Exporta cookies/tokens para uso em httpx
    """
    
    def __init__(
        self,
        user_data_dir: str = "./browser-profile",
        headless: bool = False,
        monitor_url: str = None  # Descobrir via investigação
    ):
        self.user_data_dir = Path(user_data_dir)
        self.headless = headless
        self.monitor_url = monitor_url or "https://monitor.pedidos10.com.br"
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.state: SessionState = SessionState.AUTH_REQUIRED
        
    def start(self) -> SessionState:
        """Inicia ou reconecta sessão do Pedidos10."""
        
        with sync_playwright() as p:
            # Lançar contexto persistente (como Baileys auth state)
            self.context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless
            )
            
            self.page = self.context.new_page()
            self.page.goto(self.monitor_url)
            
            # Verificar se está autenticado
            if self._is_authenticated():
                self.state = SessionState.CONNECTED
                self._save_session_backup()
            else:
                self.state = SessionState.AUTH_REQUIRED
            
            return self.state
    
    def _is_authenticated(self) -> bool:
        """Verifica se sessão está autenticada."""
        # TODO: Detectar elemento que indica login (e.g., nome do usuário, botão logout)
        # Por ora, placeholder
        
        # Exemplo: Verificar se há cookie de sessão
        cookies = self.context.cookies()
        auth_cookies = [c for c in cookies if 'session' in c['name'].lower() or 'auth' in c['name'].lower()]
        
        return len(auth_cookies) > 0
    
    def _save_session_backup(self):
        """Exporta sessão para backup (como Baileys creds.json)."""
        backup_dir = Path("./session-backup")
        backup_dir.mkdir(exist_ok=True)
        
        # Salvar storage state (cookies + localStorage)
        self.context.storage_state(path=str(backup_dir / "storage_state.json"))
        
        # Extrair tokens específicos do Pedidos10
        tokens = self._extract_tokens()
        with open(backup_dir / "pedidos10_tokens.json", 'w') as f:
            json.dump(tokens, f, indent=2)
    
    def _extract_tokens(self) -> dict:
        """Extrai tokens de autenticação do browser."""
        # TODO: Investigar onde Pedidos10 armazena tokens
        # Possíveis lugares: cookies, localStorage['authToken'], etc.
        
        tokens = {}
        
        # Cookies relevantes
        cookies = self.context.cookies()
        tokens['cookies'] = {c['name']: c['value'] for c in cookies}
        
        # localStorage
        try:
            tokens['localStorage'] = self.page.evaluate('''
                () => Object.assign({}, window.localStorage)
            ''')
        except:
            tokens['localStorage'] = {}
        
        return tokens
    
    def close(self):
        """Fecha browser mantendo estado persistido."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
```

### 5.3 Network Observer

```python
# app/browser/network_observer.py

import json
from datetime import datetime
from typing import List, Dict, Any, Callable
from playwright.sync_api import Page, Request, Response, WebSocket

class NetworkObserver:
    """
    Intercepta e registra todas as requisições de rede do Pedidos10.
    
    Similar ao que Baileys faz com WebSocket frames, mas para HTTP.
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.requests: List[Dict[str, Any]] = []
        self.websockets: List[Dict[str, Any]] = []
        
        # Setup listeners
        page.on('request', self._on_request)
        page.on('response', self._on_response)
        page.on('websocket', self._on_websocket)
    
    def _on_request(self, req: Request):
        """Captura requisição."""
        record = {
            'type': 'request',
            'method': req.method,
            'url': req.url,
            'headers': dict(req.headers),
            'post_data': req.post_data,
            'resource_type': req.resource_type,
            'timestamp': datetime.now().isoformat()
        }
        
        # Capturar body JSON se aplicável
        if req.method == 'POST' and req.post_data:
            try:
                record['post_data_json'] = json.loads(req.post_data)
            except:
                pass
        
        self.requests.append(record)
        
        # Log em tempo real
        if 'order' in req.url.lower() or 'api' in req.url.lower():
            print(f"[REQUEST] {req.method} {req.url}")
    
    def _on_response(self, res: Response):
        """Captura resposta."""
        record = {
            'type': 'response',
            'url': res.url,
            'status': res.status,
            'headers': dict(res.headers),
            'timestamp': datetime.now().isoformat()
        }
        
        # Capturar body JSON se aplicável
        content_type = res.headers.get('content-type', '')
        if 'application/json' in content_type:
            try:
                record['body_json'] = res.json()
            except:
                pass
        
        self.requests.append(record)
        
        # Log em tempo real
        if 'order' in res.url.lower() or 'api' in res.url.lower():
            print(f"[RESPONSE] {res.status} {res.url}")
    
    def _on_websocket(self, ws: WebSocket):
        """Captura WebSocket."""
        print(f"[WEBSOCKET] Conexão aberta: {ws.url}")
        
        ws_record = {
            'type': 'websocket',
            'url': ws.url,
            'opened_at': datetime.now().isoformat(),
            'frames': []
        }
        
        # Capturar frames
        ws.on('framesreceived', lambda frames: self._on_ws_frames(ws_record, frames, 'received'))
        ws.on('framessent', lambda frames: self._on_ws_frames(ws_record, frames, 'sent'))
        
        self.websockets.append(ws_record)
    
    def _on_ws_frames(self, ws_record: dict, frames, direction: str):
        """Captura frames WebSocket."""
        for frame in frames:
            ws_record['frames'].append({
                'direction': direction,
                'payload': frame.payload[:500] if len(frame.payload) > 500 else frame.payload,
                'timestamp': datetime.now().isoformat()
            })
    
    def save_traffic(self, filepath: str = "traffic-analysis.json"):
        """Salva tráfego capturado em arquivo."""
        data = {
            'requests': self.requests,
            'websockets': self.websockets,
            'captured_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Tráfego salvo em {filepath}")
    
    def get_api_endpoints(self) -> List[Dict[str, Any]]:
        """Extrai endpoints de API descobertos."""
        endpoints = []
        seen_urls = set()
        
        for req in self.requests:
            if req['type'] == 'request' and 'api' in req['url'].lower():
                url = req['url']
                if url not in seen_urls:
                    seen_urls.add(url)
                    endpoints.append({
                        'method': req['method'],
                        'url': url,
                        'has_body': req.get('post_data') is not None
                    })
        
        return endpoints
```

---

## 6. FLUXO DE IMPLEMENTAÇÃO

### Fase 1: Descoberta (Observação)

```python
# scripts/observe-traffic.py

from app.browser.session_manager import Ped10SessionManager
from app.browser.network_observer import NetworkObserver

def main():
    # 1. Iniciar sessão
    manager = Ped10SessionManager(
        headless=False  # Headful para login
    )
    
    state = manager.start()
    
    if state == SessionState.AUTH_REQUIRED:
        print("Faça login no Pedidos10 no browser aberto...")
        input("Pressione Enter após login...")
        
        if manager._is_authenticated():
            manager._save_session_backup()
            print("Sessão salva!")
    
    # 2. Observar tráfego
    observer = NetworkObserver(manager.page)
    
    print(f"Navegando para {manager.monitor_url}...")
    manager.page.goto(manager.monitor_url)
    
    print("Observando tráfego por 60 segundos...")
    print("Interaja com o painel (adicione filtros, clique em pedidos, etc.)")
    
    manager.page.wait_for_timeout(60000)
    
    # 3. Salvar descobertas
    observer.save_traffic('docs/traffic-analysis.json')
    
    # 4. Extrair endpoints
    endpoints = observer.get_api_endpoints()
    print(f"\nEndpoints descobertos: {len(endpoints)}")
    for ep in endpoints:
        print(f"  {ep['method']} {ep['url']}")
    
    manager.close()

if __name__ == "__main__":
    main()
```

### Fase 2: Documentar Protocolo

```markdown
# docs/observed-api.md

## Pedidos10 API Observada

### Autenticação
- **Mecanismo**: Session cookie + CSRF token
- **Cookie principal**: `pedidos10_session` (nome hipotético)
- **Header obrigatório**: `X-CSRF-Token` (hipotético)

### Endpoints Observados

#### Listar Pedidos
```
GET /api/v1/orders?status=pending&merchant_id={MERCHANT_ID}

Headers:
  Cookie: pedidos10_session=...
  X-Requested-With: XMLHttpRequest

Response 200:
{
  "orders": [
    {
      "id": "12345",
      "customer_name": "João Silva",
      "total": 45.90,
      "status": "pending",
      ...
    }
  ]
}
```

#### Detalhes do Pedido
```
GET /api/v1/orders/{ORDER_ID}

Response 200:
{
  "id": "12345",
  "customer": {...},
  "items": [...],
  "delivery": {...},
  "payments": [...]
}
```

### Mecanismo de Push
- **Tipo**: WebSocket / SSE / Polling (descobrir na observação)
- **URL**: (descobrir)
- **Protocolo**: (descobrir)

### Confiança
- [ ] Confirmado em sessão real
- [ ] Payloads validados
- [ ] Headers documentados
```

### Fase 3: Implementar Client

```python
# app/pedidos10/client.py

import httpx
from typing import List, Dict, Any

class Pedidos10Client:
    """
    Cliente HTTP para API do Pedidos10.
    
    SOMENTE métodos que foram observados e documentados.
    """
    
    def __init__(self, tokens: Dict[str, str], base_url: str):
        self.tokens = tokens
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)
    
    def _get_headers(self) -> Dict[str, str]:
        """Constrói headers baseados nos tokens extraídos."""
        headers = {}
        
        # TODO: Descobrir headers exatos na investigação
        if 'cookies' in self.tokens:
            cookie_str = '; '.join([f"{k}={v}" for k, v in self.tokens['cookies'].items()])
            headers['Cookie'] = cookie_str
        
        # Possível CSRF token
        if 'localStorage' in self.tokens and 'csrf_token' in self.tokens['localStorage']:
            headers['X-CSRF-Token'] = self.tokens['localStorage']['csrf_token']
        
        return headers
    
    def get_orders(self, status: str = "pending") -> List[Dict[str, Any]]:
        """Lista pedidos (endpoint observado)."""
        # TODO: URL real a descobrir
        response = self.client.get(
            '/api/v1/orders',
            params={'status': status},
            headers=self._get_headers()
        )
        
        response.raise_for_status()
        return response.json().get('orders', [])
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Obtém detalhes do pedido (endpoint observado)."""
        response = self.client.get(
            f'/api/v1/orders/{order_id}',
            headers=self._get_headers()
        )
        
        response.raise_for_status()
        return response.json()
```

---

## 7. SEGURANÇA E BOAS PRÁTICAS

### 7.1 Regras de Ouro

1. **NUNCA** commitar `browser-profile/` ou `session-backup/`
2. **NUNCA** logar cookies, tokens ou Authorization headers
3. **SEMPRE** sanitizar logs antes de salvar
4. **SOMENTE** observar tráfego da nossa própria conta
5. **ZERO** operações de escrita na Fase 1

### 7.2 .gitignore

```gitignore
# Pedidos10 Bridge
browser-profile/
session-backup/
*.json
!package*.json

# Logs
*.log
logs/

# Env
.env
.env.local

# Traffic analysis (pode conter dados sensíveis)
traffic-*.json
```

### 7.3 Logs Sanitizados

```python
def sanitize_request_for_log(request: dict) -> dict:
    """Remove dados sensíveis antes de logar."""
    sanitized = request.copy()
    
    # Remover cookies
    if 'headers' in sanitized and 'cookie' in sanitized['headers']:
        sanitized['headers']['cookie'] = '[REDACTED]'
    
    # Remover Authorization
    if 'headers' in sanitized and 'authorization' in sanitized['headers']:
        sanitized['headers']['authorization'] = '[REDACTED]'
    
    # Remover tokens no body
    if 'post_data_json' in sanitized:
        if 'token' in sanitized['post_data_json']:
            sanitized['post_data_json']['token'] = '[REDACTED]'
    
    return sanitized
```

---

## 8. COMPARAÇÃO FINAL: BAILEYS vs PEDIDOS10-BRIDGE

| Aspecto | Baileys (WhatsApp) | Pedidos10-Bridge |
|---------|--------------------|--------------------|
| **Protocolo** | WebSocket + Protobuf (engenharia reversa) | HTTP REST observado + possível WebSocket |
| **Autenticação** | QR Code + Signal protocol | Login manual + cookies persistentes |
| **Persistência** | `useMultiFileAuthState` (arquivos JSON) | `launch_persistent_context` (perfil Chromium) + `storage_state()` |
| **Observação** | Protocolo público documentado | Captura de rede via Playwright |
| **Criptografia** | Noise protocol + Signal E2E | HTTPS (TLS) |
| **Engine** | Node.js puro (WebSocket client) | Playwright + Chromium primeiro, depois httpx |
| **Licença** | Não-oficial, uso por sua conta | Uso legítimo de nossa própria conta |
| **Write ops** | Completas (send messages, groups...) | READ-ONLY inicialmente |
| **Substituição** | Permanente (sem API oficial) | Temporário → Open Delivery oficial |

---

## 9. PRÓXIMOS PASSOS

1. **Criar spike de descoberta**:
   - Script Python que abre Playwright
   - Navega para Pedidos10
   - Login manual
   - Observa tráfego por 5 minutos
   - Salva endpoints descobertos

2. **Documentar observações**:
   - Em `docs/observed-api.md`
   - Endpoints, métodos, headers, payloads

3. **Implementar SessionManager**:
   - Gerenciar perfil persistente
   - Detectar sessão expirada
   - Extrair cookies/tokens

4. **Implementar Client**:
   - SOMENTE endpoints observados
   - READ-ONLY primeiro

5. **Integrar ao DominusLabs**:
   - Usar infraestrutura existente (`PlatformTokenManager`, `OpenDeliveryAdapter`)
   - Bridge como adapter temporário

---

## 10. TECNOLOGIAS NECESSÁRIAS

```txt
# requirements.txt

playwright>=1.40.0
httpx>=0.25.0
fastapi>=0.104.0
pydantic>=2.0.0
uvicorn>=0.24.0
python-dotenv>=1.0.0
```

**Instalação:**
```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Conclusão

O **Pedidos10-Bridge** seguirá a **filosofia do Baileys**:
- Sessão persistente (login uma vez, reutilizar sempre)
- Observatory-first (observar antes de implementar)
- Read-only inicialmente
- Projetado para substituição futura (Open Delivery)

A diferença fundamental é que **não fazemos engenharia reversa do protocolo**, apenas **observamos e reproduzimos requests legítimos** da nossa própria sessão autenticada.

---

**Elaborado para validação antes da implementação.**
**Nenhum endpoint foi presumido — todos devem ser descobertos via observação real.**
