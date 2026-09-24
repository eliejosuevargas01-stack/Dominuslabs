# FALLBACK AUDIT — ARCH-001

> Data: 2026-09-24
> Escopo: dominuslabs backend + frontend, api-whatsapp-service, idc-dominuslabs
> Tipo: Read-only audit — nenhum código modificado

---

## Sumário Executivo

| Classificação | Ocorrências | Ação |
|--------------|-------------|------|
| 🔴 SECURITY_FALLBACK | 6 | Remover defaults, fail-closed |
| 🔴 DATA_INTEGRITY_FALLBACK | 4 | Remover hardcoded metrics |
| 🔴 SESSION_FALLBACK | 4 | Eliminar seleção automática de sessão |
| 🟡 CONFIG_FALLBACK | 18 | Documentar ou remover |
| 🟢 SAFE_UI_DEFAULT | 12 | Manter com documentação |
| 🟢 SAFE_FORMATTING_DEFAULT | 8 | Manter |

---

## 🔴 SECURITY_FALLBACK

### SEC-001 — config.py:48
**Arquivo:** `project-hub/backend/app/core/config.py:48`
```python
SECRET_KEY: str = os.getenv("JWT_SECRET", "")
```
**Risco:** JWT_SECRET vazio permite assinar tokens com chave vazia — autenticação completamente comprometida.
**Ação:** Remover default `""`. Fail-closed via startup validator (ARCH-002 já cobre).

---

### SEC-002 — config.py:41
**Arquivo:** `project-hub/backend/app/core/config.py:41`
```python
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
```
**Risco:** Senha admin vazia permite login sem credencial.
**Ação:** Remover default `""`. Fail-closed via startup validator.

---

### SEC-003 — config.py:101
**Arquivo:** `project-hub/backend/app/core/config.py:101`
```python
DOMINUS_PRIVATE_KEY: str = os.getenv("DOMINUS_PRIVATE_KEY", "")
```
**Risco:** Chave privada vazia quebra criptografia assimétrica silenciosamente — payloads podem ser forjados.
**Ação:** Remover default `""`. Fail-closed via startup validator.

---

### SEC-004 — config.py:104
**Arquivo:** `project-hub/backend/app/core/config.py:104`
```python
IDPW_PUBLIC_KEY: str = os.getenv("IDPW_PUBLIC_KEY", "")
```
**Risco:** Chave pública IDPW vazia impede validação de JWT M2M — bypass de autenticação entre serviços.
**Ação:** Remover default `""`. Fail-closed via startup validator.

---

### SEC-005 — config.py:80-81
**Arquivo:** `project-hub/backend/app/core/config.py:80-81`
```python
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
N8N_WEBHOOK_SECRET: str = os.getenv("N8N_WEBHOOK_SECRET", "")
```
**Risco:** Webhook secret vazio permite que qualquer origem poste eventos falsos no CRM.
**Ação:** Remover default `""`. Deprecar `WEBHOOK_SECRET` em favor de `N8N_WEBHOOK_SECRET`.

---

### SEC-006 — config.py carrega .env.example
**Arquivo:** `project-hub/backend/app/core/config.py:9-10`
```python
if os.path.exists(".env.example"):
    load_dotenv(".env.example")
```
**Risco:** Placeholders do `.env.example` (ex: `your-private-key-hex-or-pem`) são carregados como valores reais de produção. **CORRIGIDO em ARCH-002.**
**Ação:** ✅ Corrigido — removido carregamento de `.env.example`.

---

## 🔴 DATA_INTEGRITY_FALLBACK

### DAT-001 — DashboardOperationalView.tsx:132
**Arquivo:** `src/pages/DashboardOperationalView.tsx:132`
```typescript
const activeSet = todayList.length > 0 ? todayList : rawList;
```
**Risco:** "Pedidos Hoje" exibe histórico completo quando hoje está vazio — dados falsos para o operador.
**Ação:** Eliminar fallback. `todayList` é sempre a lista correta, mesmo vazia. (DATA-001)

---

### DAT-002 — DashboardOperationalView.tsx:178
**Arquivo:** `src/pages/DashboardOperationalView.tsx:178`
```typescript
atendimentosIa: iaCount || 14,
```
**Risco:** Exibe 14 atendimentos IA quando não há dados — métrica inventada.
**Ação:** Remover `|| 14`. Exibir `—` ou `null` quando não calculável. (DATA-002)

---

### DAT-003 — DashboardOperationalView.tsx:179
**Arquivo:** `src/pages/DashboardOperationalView.tsx:179`
```typescript
atendimentosHumanos: humanCount || 2,
```
**Risco:** Exibe 2 atendimentos humanos quando não há dados.
**Ação:** Remover `|| 2`. Exibir `—` ou `null`. (DATA-002)

---

### DAT-004 — DashboardOperationalView.tsx:180
**Arquivo:** `src/pages/DashboardOperationalView.tsx:180`
```typescript
porcentagemIa: pctIa > 0 ? pctIa : 88
```
**Risco:** Exibe 88% IA quando não há dados — número completamente inventado.
**Ação:** Remover `: 88`. Exibir `—` ou `null`. (DATA-002)

---

## 🔴 SESSION_FALLBACK

### SES-001 — OmnichannelView.tsx:840
**Arquivo:** `src/pages/OmnichannelView.tsx:840`
```typescript
const workingSession = availableSessions.find(s => s.status === 'WORKING') || availableSessions[0];
setActiveSendSession(workingSession.id || '');
```
**Risco:** Se nenhuma sessão está WORKING, seleciona silenciosamente a primeira disponível — pode enviar mensagens pela sessão errada (potencialmente desconectada).
**Ação:** Nunca selecionar sessão automaticamente. Mostrar estado desconectado e exigir ação do usuário.

---

### SES-002 — OmnichannelView.tsx:1027
**Arquivo:** `src/pages/OmnichannelView.tsx:1027`
```typescript
|| (availableSessions.find(s => s.status === 'WORKING') || availableSessions[0])?.id || '';
```
**Risco:** Mesmo padrão — fallback para primeira sessão disponível sem verificar status.
**Ação:** Eliminar fallback. Exigir sessão explicitamente selecionada e conectada.

---

### SES-003 — OmnichannelView.tsx:1142
**Arquivo:** `src/pages/OmnichannelView.tsx:1142`
```typescript
|| (availableSessions.find(s => s.status === 'WORKING') || availableSessions[0])?.id || '';
```
**Risco:** Idem SES-002.
**Ação:** Eliminar fallback.

---

### SES-004 — OmnichannelView.tsx:2148
**Arquivo:** `src/pages/OmnichannelView.tsx:2148`
```typescript
session_id: (activeSendSession && activeSendSession !== 'default' ? activeSendSession : null) || (availableSessions.find(s => s.status === 'WORKING') || availableSessions[0])?.id || '',
```
**Risco:** Envio de mensagem pode usar sessão não selecionada pelo usuário.
**Ação:** Bloquear envio se nenhuma sessão explicitamente selecionada e conectada.

---

## 🟡 CONFIG_FALLBACK

### CFG-001 — config.py:96
**Arquivo:** `project-hub/backend/app/core/config.py:96`
```python
WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "http://localhost:3000")
```
**Risco:** Em produção, fallback para localhost pode causar falhas silenciosas de integração.
**Ação:** Remover default. Fail-closed via startup validator (ARCH-002 já cobre).

---

### CFG-002 — config.py:97
**Arquivo:** `project-hub/backend/app/core/config.py:97`
```python
WHATSAPP_PUBLIC_URL: str = os.getenv("WHATSAPP_PUBLIC_URL", "https://dominuslabs.online")
```
**Risco:** URL de produção hardcoded como default — pode expor URL real em ambientes errados.
**Ação:** Remover default. Fail-closed via startup validator.

---

### CFG-003 — config.py:98
**Arquivo:** `project-hub/backend/app/core/config.py:98`
```python
IDENTITY_WORKER_URL: str = os.getenv("IDENTITY_WORKER_URL", "https://idc-dominuslabs.eliejosuevargas01.workers.dev")
```
**Risco:** URL real do IDPW hardcoded como default — expõe infraestrutura em código público.
**Ação:** Remover default. Fail-closed via startup validator.

---

### CFG-004 — config.py:40
**Arquivo:** `project-hub/backend/app/core/config.py:40`
```python
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
```
**Risco:** Username admin previsível. Não é secret, mas facilita brute force.
**Ação:** Manter default documentado, mas logar warning em produção.

---

### CFG-005 — config.py:43
**Arquivo:** `project-hub/backend/app/core/config.py:43`
```python
ADMIN_TENANT_ID: str = os.getenv("ADMIN_TENANT_ID", os.getenv("MASTER_TENANT_ID", "admin"))
```
**Risco:** Tenant ID admin previsível.
**Ação:** Manter default documentado, mas logar warning em produção.

---

### CFG-006 — config.py:44
**Arquivo:** `project-hub/backend/app/core/config.py:44`
```python
VIEWER_USERNAME: str = os.getenv("VIEWER_USERNAME", "patrik182rodrigues@gmail.com")
```
**Risco:** Email real hardcoded como default de viewer — expõe email pessoal em código.
**Ação:** Remover email real. Usar placeholder neutro como default.

---

### CFG-007 — main.py:361, 391
**Arquivo:** `project-hub/backend/app/main.py:361, 391`
```python
static_dir = os.getenv("STATIC_DIR", "/app/static")
```
**Risco:** Path hardcoded pode não existir em todos os ambientes.
**Ação:** Manter como SAFE — path estrutural, não sensível.

---

### CFG-008 — wa-api: src/index.js:123
**Arquivo:** `api-whatsapp-service/src/index.js:123`
```javascript
host: process.env.HOST || "0.0.0.0",
```
**Risco:** Bind em todas as interfaces por default — aceitável para container, mas deve ser documentado.
**Ação:** Manter. Documentar como SAFE (container padrão).

---

### CFG-009 — wa-api: src/index.js:134-136
**Arquivo:** `api-whatsapp-service/src/index.js:134-136`
```javascript
sessionsDir: path.resolve(process.env.SESSIONS_DIR || path.join(__dirname, "..", "sessions")),
dataDir: path.resolve(process.env.DATA_DIR || path.join(__dirname, "..", "data")),
mediaDir: path.resolve(process.env.MEDIA_DIR || path.join(__dirname, "..", "data", "media")),
```
**Risco:** Paths derivados do filesystem — não sensíveis, mas devem ser documentados.
**Ação:** Manter. Documentar como SAFE (path estrutural).

---

### CFG-010 — wa-api: session.service.js:230
**Arquivo:** `api-whatsapp-service/src/services/session.service.js:230`
```javascript
optOutKeywords: (process.env.ANTIBAN_OPTOUT_KEYWORDS || 'sair,stop,parar,cancelar,unsubscribe')
```
**Risco:** Keywords padrão hardcoded — comportamento de negócio inventado.
**Ação:** Manter como SAFE_UI_DEFAULT (keywords de opt-out são padrão da indústria).

---

## 🟢 SAFE_UI_DEFAULT (Manter)

### SAFE-001 — wa-api: settings.routes.js:95
```javascript
message: error?.message || 'Nao foi possivel salvar as configuracoes da sessao.',
```
**Contexto:** Mensagem de erro amigável quando a original é vazia. Não altera semântica.
**Ação:** Manter.

---

### SAFE-002 — wa-api: settings.routes.js:236
```javascript
label: request.body.label || 'Novo Webhook',
```
**Contexto:** Label padrão para webhook sem nome. UI cosmetic.
**Ação:** Manter.

---

### SAFE-003 — wa-api: messages.routes.js:129
```javascript
message: error?.message || 'Nao foi possivel enviar a mensagem.',
```
**Contexto:** Mensagem de erro amigável. Não altera semântica.
**Ação:** Manter.

---

### SAFE-004 — wa-api: utils.js:107
```javascript
const base = slugify(name) || 'sessao';
```
**Contexto:** Slug padrão quando o nome não gera slug válido. UI cosmetic.
**Ação:** Manter.

---

### SAFE-005 — wa-api: utils.js:137
```javascript
name: metadata.name || 'Session',
```
**Contexto:** Nome padrão de sessão quando metadata não tem nome. UI cosmetic.
**Ação:** Manter.

---

### SAFE-006 — wa-api: health.routes.js:112
```javascript
const status = s.snapshot?.status || 'idle';
```
**Contexto:** Status padrão para health check. Semântica clara.
**Ação:** Manter.

---

## 🟢 SAFE_FORMATTING_DEFAULT (Manter)

### FMT-001 — wa-api: message.model.js (múltiplas linhas)
```javascript
jid: message.jid || "",
type: message.type || "text",
status: message.status || "stored",
text: message.text || "",
```
**Contexto:** Normalização de campos opcionais do Baileys para strings vazias. Não altera semântica — apenas evita null/undefined.
**Ação:** Manter. Documentar como normalização de schema.

---

### FMT-002 — wa-api: message.model.js:157-163
```javascript
kind: media.kind || "document",
mimeType: media.mimeType || "application/octet-stream",
fileSize: Number(media.fileSize || 0) || null,
```
**Contexto:** Defaults de formatação para mídia. Não altera dados reais.
**Ação:** Manter.

---

### FMT-003 — wa-api: contact.model.js:38-49
```javascript
const id = String(entry?.id || entry?.lid || entry?.jid || fallbackJid || "").trim();
jid: entry?.jid || fallbackJid || "",
```
**Contexto:** Normalização de IDs de contato com múltiplos formatos possíveis (id/lid/jid). Não é fallback — é resolução de identidade.
**Ação:** Manter.

---

## IDC-Dominuslabs

Nenhum fallback identificado no IDC. Todas as configurações usam `process.env.X` sem default funcional. ✅

---

## Plano de Ação Resumido

| Prioridade | Itens | Task |
|-----------|-------|------|
| 🔴 P0 | SEC-001..006 | ARCH-002 (em andamento) + ARCH-003 |
| 🔴 P0 | DAT-001..004 | DATA-001 + DATA-002 |
| 🔴 P0 | SES-001..004 | OMN-001 (Fase 7) |
| 🟡 P1 | CFG-001..006 | ARCH-003 |
| 🟢 P2 | SAFE + FMT | Documentar, manter |
