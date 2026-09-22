# GOAL — Pedidos10 Bridge

## Objetivo
Implementar um módulo integrado ao DominusLabs backend que:
1. Conecta ao sistema Pedidos10 via **API REST (httpx)** para autenticação e dados
2. Recebe notificações de pedidos em **tempo real via AWS IoT Core MQTT over WebSocket (SigV4)**
3. Armazena credenciais com **AES-256-GCM via `credential_vault.py` existente**
4. Roda como **serviço assíncrono interno** ao FastAPI — sem Playwright, sem polling externo

## Localização
```
/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/pedidos10/
```
Módulo **totalmente isolado**. Zero modificações em arquivos existentes do DominusLabs sem aprovação explícita do Captain.

## Premissas e Descobertas Confirmadas

### API REST Pedidos10
- **Base URL**: `https://api-monitor.pedidos10.com.br/api-gestor-V1`
- **Token server** (fixo, hardcoded no JS): `Ykdsae584sderopOuesOpaeo90`
- **App name**: `Pedidos10-Gestor`
- **Origem**: `12`, versão `1`, des-versao `2.0.25`

### Payload de Login (sem reCAPTCHA — confirmado funcionando)
```json
POST /auth
{
  "des_login": "<email>",
  "des_senha": "<senha>",
  "des_recaptcha_token": "",
  "app_name": "Pedidos10-Gestor",
  "id_origem": "12",
  "num_versao": 1,
  "des_versao": "2.0.25",
  "token-server": "Ykdsae584sderopOuesOpaeo90",
  "token-u": null
}
```
**Resposta**: `{ "jwt": "<JWT>", "des_token": "<token_u>" }`

### Auth Pattern Padrão (todas as outras requisições)
URL path suffix: `token-server/{LP}/id-origem/12/num-versao/1/des-versao/2.0.25/token-u/{token_u}`
Headers: `Authorization: <JWT>`, `x-token: Ykdsae584sderopOuesOpaeo90`

### Endpoints Mapeados
| Endpoint | Método | Uso |
|---|---|---|
| `/auth` | POST | Login → JWT + token-u |
| `/config-env/{qt()}` | GET | Credenciais MQTT (encriptadas AES-ECB) |
| `/usuario/{qt()}` | GET | Dados do usuário + lista de merchants com `des_channel_websocket` |
| `/estabelecimento-cardapio/{qt()}` | GET | Catálogo de produtos |
| `/lista-pedidos/{qt()}` | GET | Lista de pedidos |
| `/lista-pedidos-aguardando-confirmacao/{qt()}` | GET | Pedidos pendentes |
| `/estabelecimento-abertura/{qt()}` | GET | Status de abertura |

### Notificações em Tempo Real — AWS IoT Core MQTT
- **Protocolo**: MQTT over WebSocket com SigV4 presigned URL
- **Credenciais**: vêm do `/config-env` → `mqtt_region`, `mqtt_endpoint`, `mqtt_key_id`, `mqtt_secret_key`
- **Tópico MQTT**: `des_channel_websocket` (campo por merchant, retornado em `/usuario`)
- **Eventos recebidos** via `ind_evento`:
  - `"pedido"` → novo pedido / atualização
  - `"mensagem"` → mensagem do cliente
  - `"fechamento-estabelecimento"` → loja fechou
  - `"impressao"` → comando de impressão (ignorar no bridge)

### Criptografia das Credenciais (at-rest)
- Reutiliza **`app.core.credential_vault.encrypt_credentials / decrypt_credentials`** existente
- AES-256-GCM com chave derivada via HKDF-SHA256 da `DOMINUS_PRIVATE_KEY`
- Armazena no campo `credentials_enc` da tabela `tenant_platform_integrations`

### Decriptação do config-env
- O Pedidos10 encripta o config-env com **AES-ECB + PKCS7** usando chave `YL = "dsadas*iusdasda&uUisoidas45p0"`
- Implementar decifragem via `cryptography.hazmat.primitives.ciphers` (AES-ECB)
- **Fallback**: se a decriptação falhar, o bridge opera sem MQTT e usa polling mínimo (60s)

## Restrições Absolutas
- ❌ NÃO modificar nenhum arquivo fora de `app/pedidos10/` sem aprovação explícita
- ❌ NÃO alterar `main.py`, `router.py`, modelos, migrations ou qualquer serviço existente
- ❌ NÃO usar Playwright em nenhuma parte do bridge
- ❌ NÃO expor email/senha em logs, prints ou respostas de API
- ✅ Toda integração com o backend existente via **importação direta** (sem modificar os arquivos-fonte)
- ✅ Registro no router feito via **inclusão externa** — o Captain confirma antes de aplicar

## Definição de Pronto
1. Módulo roda isolado com `python -m app.pedidos10.cli --help`
2. Script de smoke test confirma login + config-env + conexão MQTT
3. Eventos MQTT recebidos são logados e publicáveis via callback
4. Credenciais persistidas e decriptadas corretamente via `credential_vault`
5. Reauth automático funciona ao simular 401
6. Zero arquivos do DominusLabs existentes modificados
