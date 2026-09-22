# DominusLabs — Task Backlog
> Gerado automaticamente em 22/09/2026. Atualizar ao completar cada tarefa.

---

## Legenda
- 🔴 Crítico / Bloqueante
- 🟡 Importante
- 🟢 Melhoria
- ✅ Concluído
- 🚧 Em progresso
- ⬜ Pendente

---

## Grafo de Dependências

```
T1 ──► T2 ──► T3 ──► T10
       │
T5 ────┤ (paralelo com T1)
T6 ────┤ (paralelo com tudo)
T7 ────┤
T8 ────┤
T11 ───┤ (paralelo com T3)
T4 ────┘ (docs, totalmente paralelo)
T9 ─────  (paralelo com T6)
T12 ────  (qualquer momento)
```

---

## T1 — 🔴 [WA API] Mídia: persistência + link customizado
**Status:** ⬜ Pendente  
**Bloqueia:** T2, T3, T10  
**Paralelo com:** T4, T5, T6, T7, T8

### Contexto
- `/app/data` já está em bind mount persistente (confirmado: `bind /app/data → /app/data`)
- O WA API já baixa mídias via `cacheMediaBuffer` e `resolveMediaDelegate`
- Porém o webhook é disparado **antes** do download completar em mensagens recebidas (`handleMessagesUpsert`)
- O `media_url` enviado no webhook é `/api/sessions/{sessionId}/media?messageId={id}` (correto), mas o n8n salva `JSON.stringify(media)` no banco

### O que fazer
1. Em `handleMessagesUpsert`: aguardar `resolveMessageMedia(storedMessage)` antes de `dispatchWebhookMessage`
2. Renomear arquivo salvo para: `{sessionId}_{jid_clean}_{timestamp}.{ext}`
   - Exemplo: `eliezer-sc_178189703839815@lid_1790113823.jpg`
   - `jid_clean` = JID/LID sem caracteres especiais para filesystem
3. Garantir que `media.url` no payload do webhook sempre aponta para o link interno
4. Verificar que volume `/app/data` sobrevive a deploys no Coolify

### Arquivos
- `src/managers/session.manager.js` — `handleMessagesUpsert`, `resolveMediaDelegate`
- `src/models/message.model.js` — `serializeMediaForClient`

---

## T2 — 🔴 [n8n] Corrigir `salva mensagem1` — media_url como link, não objeto
**Status:** ⬜ Pendente  
**Depende de:** T1  
**Paralelo com:** T3

### Contexto
- Nó `salva mensagem1` no workflow `SpQwyDZsOo3ozXuE` salva:
  ```
  media_url = JSON.stringify(payload.message.media)  ← ERRADO
  ```
- Deveria salvar:
  ```
  media_url = payload.message.media.url  ← /api/sessions/.../media?messageId=...
  ```

### O que fazer
1. Editar o nó `salva mensagem1` no n8n
2. Alterar `media_url` para `={{ $('Validar HMAC').item.json.payload.message.media?.url ?? null }}`

---

## T3 — 🟡 [Frontend] Renderização de mídia — media_url é JSON object, não URL
**Status:** ⬜ Pendente  
**Depende de:** T2  
**Paralelo com:** T5, T11

### Contexto
- O banco `messages.media_url` contém JSON stringificado do objeto media
- `OmnichannelView.tsx` tenta usar como URL diretamente → falha ao renderizar imagens/vídeos

### O que fazer
1. No helper `DeMediaUrl` / `serializeMediaForClient` do frontend:
   - Tentar `JSON.parse(media_url)` → se sucesso, usar `.url` do objeto
   - Se for string começando com `/api/`, usar diretamente
2. Testar renderização de imagem, vídeo, áudio e documento

### Arquivos
- `src/pages/OmnichannelView.tsx` — função `Ae` (renderização de mídia)

---

## T4 — 🟢 [DOCS] Documentação completa do sistema
**Status:** ⬜ Pendente  
**Paralelo com:** tudo  
**Subagentes:** Low, um arquivo por vez (evitar limite TPM)

### Arquivos a criar em `/home/eliezer/Escritorio/dominuslabs/docs/`
| Arquivo | Conteúdo |
|---|---|
| `architecture.md` | Visão geral, containers, fluxo de dados, portas, rede |
| `wa-api.md` | Endpoints, auth JWT, webhook payload format, exemplos |
| `frontend-omnichannel.md` | Componentes, SSE flow, dedup logic, scroll behavior |
| `n8n-workflows.md` | dominuslabs_respostas_leads, dominuslabs_crm, Dominus AI |
| `media-pipeline.md` | Download, persist, link format, serve, volume |
| `deployment.md` | Coolify, volumes, health checks, env vars, rollback |

---

## T5 — 🟡 [WA API + Backend + Frontend] Status em tempo real (sent→delivered→read)
**Status:** ⬜ Pendente  
**Paralelo com:** T1, T4

### Contexto
- Após envio, status fica preso em `sent`
- `handleMessagesUpdate` no Baileys recebe ACKs de entrega/leitura mas pode não estar disparando webhook

### O que fazer
1. **WA API**: confirmar que `handleMessagesUpdate` chama `dispatchWebhookMessage(sessionId, msg, 'message.updated')`
2. **Backend**: `_process_update_chat` aceitar `action='message.updated'` e emitir SSE com apenas `{message_id, status}`
3. **Frontend**: SSE handler — ao receber `message.updated`, atualizar `status` de mensagem existente em `chatMessages` sem inserir nova

### Arquivos
- `src/managers/session.manager.js` — `handleMessagesUpdate`
- `project-hub/backend/app/api/endpoints/webhooks.py` — `_process_update_chat`
- `src/pages/OmnichannelView.tsx` — SSE handler

---

## T6 — 🟡 [n8n] Análise end-to-end: Dominus AI + Dominus AI Buffer
**Status:** ⬜ Pendente  
**Paralelo com:** tudo

### Workflows alvo
- `YqDBFFzJ1L4FRAvz` — Dominus AI (ativo)
- `4ANz4lSb80pCuAT4` — Dominus AI Buffer (ativo)

### O que fazer
1. Mapear todos os nós de cada workflow com função e dependências
2. Verificar execuções recentes: erros, timeouts, falhas silenciosas
3. Testar todos os casos: texto, áudio, imagem, lead novo, lead existente, grupo
4. Verificar credenciais (API keys, tokens), retries, tratamento de erros
5. Identificar e documentar cada problema
6. Aplicar fixes para cada problema encontrado

---

## T7 — 🟡 [WA API] app:null em createSessionManager — logs silenciados
**Status:** ⬜ Pendente  
**Paralelo com:** T1, T8

### Contexto
- `src/index.js` cria `sessionManager` com `app: null` antes de `createApp()`
- Resultado: `safeLog = { info: noop, warn: noop, error: noop }` — logs internos silenciados

### O que fazer
1. Criar método `sessionManager.setLogger(logger)` em `session.manager.js`
2. Em `src/index.js`, após `createApp()`: `sessionManager.setLogger(app.log)`
3. Ou: criar logger Pino standalone e passar na criação

### Arquivos
- `src/index.js`
- `src/managers/session.manager.js`

---

## T8 — 🟡 [WA API] me=null após restart de container
**Status:** ⬜ Pendente  
**Paralelo com:** T7

### Contexto
- Após deploy/restart, sessões conectam (`status=connected`) mas `me=null`
- `state.me = state.socket?.user` — WA só envia o `user` no `connection.update` open
- O PG grava `me` mas na reconexão pode não estar sendo atualizado

### O que fazer
1. Em `handleConnectionUpdate` quando `connection === 'open'`: garantir `state.me = state.socket?.user || state.me`
2. Em `persistSessions`: salvar `me` no PG ao conectar
3. Em `loadStoresFromPg`: restaurar `state.me` do PG na inicialização

---

## T9 — 🟢 [Backend] Investigar/desativar workflow legado dominuslabs_crm
**Status:** ⬜ Pendente  
**Paralelo com:** T6

### Contexto
- Workflow `WJ37gGiodnAJVkBN` (dominuslabs_crm) está ativo
- Função unclear — pode ser legado sem dependências ativas

### O que fazer
1. Verificar triggers e webhooks do workflow
2. Verificar se algum endpoint do backend o chama
3. Se sem dependências: desativar no n8n
4. Documentar decisão

---

## T10 — 🟢 [Order Manager] Implementação completa
**Status:** ⬜ Pendente  
**Depende de:** T1 + T2 + T3 + T5 finalizados  
**Escopo:** a definir com o usuário

### Contexto
- Tarefa 2 original do projeto, adiada desde o início
- PDV completo para operadores de restaurante/delivery

---

## T11 — 🟢 [Frontend] Contador de não-lidas não zera em todos os casos
**Status:** ⬜ Pendente  
**Paralelo com:** T3

### Contexto
- Ao abrir chat, `unread_count` não zera após recarregar página
- Falta endpoint `PATCH /crm/conversations/{jid}/read` ou similar

### O que fazer
1. Em `handleSelectChat`: chamar endpoint para marcar conversa como lida
2. Criar endpoint `POST /api/v1/crm/conversations/mark-read` no backend
3. Atualizar sidebar localmente via `setConversations`

---

## T12 — 🟢 [WA API] Limpeza de logs de debug residuais
**Status:** ⬜ Pendente  
**Paralelo com:** qualquer tarefa

### O que fazer
1. Verificar `src/routes/messages.routes.js` — `fastify.log.error` no catch (manter, útil)
2. Verificar `src/managers/session.manager.js` — algum `console.error` esquecido?
3. Remover apenas logs temporários de debugging, manter os de produção

---

## Histórico de Conclusões

| Data | ID | Descrição |
|---|---|---|
| 22/09/2026 | — | Backlog criado a partir do estado do sistema |

---

## Referências Rápidas

### Containers
- **DominusLabs backend**: `sjrweu7rw8e3nywm5stef2ri-*` (app 38)
- **WA API**: `hkossco0sggwwwss0cwk4w0s-*` (app 32)
- **Coolify DB**: `coolify-db`
- **VPS**: `ssh -p 2222 root@72.60.247.157`

### Repositórios
- Frontend + Backend: `/home/eliezer/Escritorio/dominuslabs`
- WA API: `/home/eliezer/Escritorio/api-whatsapp-service`

### n8n
- URL: `https://myn8n.seommerce.shop`
- Dominus AI: `YqDBFFzJ1L4FRAvz`
- Dominus AI Buffer: `4ANz4lSb80pCuAT4`
- dominuslabs_respostas_leads: `SpQwyDZsOo3ozXuE`
- dominuslabs_crm: `WJ37gGiodnAJVkBN`

### Volumes WA API (bind mounts persistentes)
- `/app/sessions` — credenciais Baileys
- `/app/data` — mídia, mensagens, conversas
- `/app/keys` — chaves criptográficas
