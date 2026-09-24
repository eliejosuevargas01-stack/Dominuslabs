# CONTRACTS — Dominus Product & Architecture Refoundation

## C1 — Zero Trust Preservation

Nenhuma mudança de UX, refatoração ou simplificação pode:

- remover tenant_id validation em qualquer endpoint
- confiar em tenant_id enviado pelo browser sem validação server-side
- remover ownership de sessão WhatsApp
- expor M2M JWT ao frontend
- expor private keys ou encryption keys
- remover JWKS validation
- relaxar scopes do IDC
- introduzir endpoints públicos de mídia sem autorização
- remover isolamento multi-tenant em queries

**Violação = bloqueio imediato da tarefa.**

---

## C2 — Fail-Closed

Configuração crítica ausente → startup recusa iniciar (exit code ≠ 0).

Valores que NUNCA podem ter fallback funcional:

- JWT_SECRET, JWT_ISSUER, JWT_AUDIENCE
- IDPW_URL, IDPW_JWKS_URL
- DATABASE_URL
- DOMINUS_PRIVATE_KEY, IDPW_PUBLIC_KEY
- WHATSAPP_API_URL, WHATS_API_PUBLIC_KEY
- N8N_WEBHOOK_SECRET
- ENCRYPTION_MASTER_KEY

Retries explícitos e limitados da mesma operação NÃO são fallback.

---

## C3 — Data Integrity

- `Pedidos Hoje` = pedidos do dia atual no timezone do tenant. Sem pedidos = 0.
- Métricas nunca usam valores hardcoded ou demonstrativos.
- Filtros de período (Hoje / 7d / 30d) alteram a query real.
- Nenhum `|| valorDefault` que altere semântica (ex: `iaCount || 14` proibido).

---

## C4 — Event Contract

Contrato base:

```json
{
  "version": 1,
  "event_id": "uuid",
  "type": "message.created",
  "tenant_id": "tenant",
  "session_id": "session",
  "occurred_at": "ISO-8601",
  "payload": {}
}
```

Regras:

- Um evento nunca muda de semântica durante o pipeline.
- `message.status.updated` NUNCA pode ser tratado como `message.created`.
- `message.status.updated` NUNCA dispara som, browser notification, ou incrementa unread.
- n8n roteia por `type`, não reconstrói o tipo.

---

## C5 — Media Ownership

- WA API é proprietária do lifecycle de mídias WhatsApp.
- Mídia persistida em `/app/data/media/{tenant}/{session}/`.
- Frontend NUNCA depende de pps.whatsapp.net, fbcdn.net ou URLs temporárias.
- State machine: pending → downloading → ready → failed.
- Falha de download NÃO invalida a mensagem.

---

## C6 — Session Ownership

- Sessão desconectada NUNCA é selecionada silenciosamente como fallback.
- `workingSession || availableSessions[0]` é proibido.
- Sessão desconectada → mostrar estado → impedir operação → ação consciente do usuário.

---

## C7 — Notification Rules

Som principal SOMENTE para: `message.created AND incoming AND não processado`.

NUNCA som para: read, played, delivered, reaction, media.ready, message.status.updated, outgoing, conversation.updated.

Browser Notification API para mensagens recebidas em background.

---

## C8 — Pagination

- Conversas: cursor pagination, 30 iniciais, IntersectionObserver.
- Mensagens: últimas 50 ao abrir, scroll up carrega anteriores com prepend + scroll anchor.
- NUNCA carregar todo o histórico inicialmente.

---

## C9 — No Implicit Fallback

Proibido:

```ts
valorReal || valorInventado
sessaoConectada || primeiraSessao
dadosHoje.length ? dadosHoje : historicoCompleto
.catch(() => {})  // em operação relevante
```

---

## C10 — Destructive Changes

Antes de deletar endpoint, função, rota, handler, componente, serviço ou workflow:
1. Localizar TODOS os consumidores (grep cross-repo + n8n).
2. Comprovar substituição.
3. Somente então remover.

---

## C11 — Code Architecture

- Não criar novos monólitos ao decompor existentes.
- Pages coordenam componentes; não implementam API + realtime + storage + media + notifications + business rules + UI complexa.
- Dividir por responsabilidade de domínio, não por linhas.

---

## C12 — Testing

- Playwright E2E nos breakpoints: 375x812, 390x844, 414x896, 768x1024, 1366x768, 1440x900, 1920x1080.
- Asserções: horizontal overflow = 0, elementos fora viewport = 0, controles sobrepostos = 0, dados fake = 0.
- Testes de regressão antes de cada mudança destrutiva.

---

## C13 — UX & Language

- Linguagem direta de operação do negócio, não corporativa artificial.
- IA apresentada como "Funcionário Digital".
- Project Hub removido da interface de tenants.
- Mobile = experiência própria, não desktop comprimido.
