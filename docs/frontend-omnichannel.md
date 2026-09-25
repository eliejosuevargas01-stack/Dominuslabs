# Omnichannel — Arquitetura Frontend

> **Status:** CANONICAL — Target Architecture

Este documento descreve a arquitetura alvo do Omnichannel, não a implementação atual.

---

## Visão Geral

O Omnichannel é o módulo de atendimento multicanal do Dominus, projetado para funcionar como um aplicativo de mensagens profissional.

---

## Arquitetura Alvo

```
features/
├── omnichannel/
│   ├── components/
│   │   ├── ConversationList/
│   │   ├── Chat/
│   │   ├── MessageBubble/
│   │   ├── MediaViewer/
│   │   ├── Avatar/
│   │   └── SessionSelector/
│   ├── hooks/
│   │   ├── useConversations.ts
│   │   ├── useMessages.ts
│   │   ├── useMedia.ts
│   │   └── useSession.ts
│   ├── api/
│   │   ├── conversations.ts
│   │   ├── messages.ts
│   │   └── media.ts
│   ├── state/
│   │   ├── conversationSlice.ts
│   │   └── messageSlice.ts
│   └── types/
│       ├── conversation.ts
│       ├── message.ts
│       └── media.ts
│
├── realtime/
│   ├── RealtimeProvider.tsx
│   ├── useRealtime.ts
│   └── handlers/
│
├── notifications/
│   ├── NotificationEngine.ts
│   ├── SoundEngine.ts
│   └── BrowserNotifications.ts
│
└── shared/
    ├── components/
    ├── hooks/
    └── utils/
```

---

## Responsabilidades por Módulo

### ConversationList

- Lista de conversas (~30 iniciais)
- Cursor pagination
- IntersectionObserver para infinite scroll
- Avatar com lazy loading
- Preview da última mensagem
- Indicador de unread

### Chat

- Lista de mensagens (~50 ao abrir)
- Scroll para cima carrega anteriores
- Mensagens prepend + scroll anchor
- MessageBubble para cada tipo
- Input de mensagem
- Upload de mídia

### MessageBubble

- Renderer específico por tipo:
  - `text`
  - `image`
  - `video`
  - `audio`
  - `document`
  - `sticker`
- Status indicators
- Timestamp
- Reply context

### MediaViewer

- Imagens: expandir, zoom, pan, fit, download, ESC
- Vídeos: expandir, player grande, fullscreen, controls, download
- Stickers: renderer próprio (128-160px)

### Avatar

- Componente único `ConversationAvatar`
- Authenticated fetch
- Lazy loading
- Cache por `tenant_id + session_id + contact_jid`
- Fallback visual com iniciais

### SessionSelector

- Lista de sessões disponíveis
- Estado visual (WORKING, DISCONNECTED, etc.)
- **NÃO seleciona sessão desconectada como fallback**

---

## Realtime

### RealtimeProvider Global

O realtime **NÃO** pertence ao OmnichannelView.

```tsx
// App.tsx
function AuthenticatedApp() {
  return (
    <RealtimeProvider>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/atendimento" element={<Omnichannel />} />
        <Route path="/pedidos" element={<Orders />} />
      </Routes>
    </RealtimeProvider>
  );
}
```

### Eventos Tratados

| Evento | Ação |
|--------|------|
| `message.created` | Atualizar chat, notification, som |
| `message.status.updated` | Atualizar status **SEM som** |
| `conversation.updated` | Reordenar lista |
| `session.connected` | Atualizar status |
| `session.disconnected` | Atualizar status |

---

## Notificações

### Som Principal

**SOMENTE para:**
- `message.created`
- AND incoming
- AND evento não processado anteriormente

**NUNCA para:**
- `message.status.updated`
- `message.reaction.updated`
- `media.ready`
- Outgoing messages
- Conversation updates

### Browser Notification

- API nativa do browser
- Clique abre Dominus → Atendimento → sessão → conversa

---

## Pagination

### Conversations

```ts
const useConversations = () => {
  const [conversations, setConversations] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  const loadMore = async () => {
    if (!hasMore) return;
    const response = await api.getConversations({ cursor, limit: 30 });
    setConversations(prev => [...prev, ...response.data]);
    setCursor(response.nextCursor);
    setHasMore(response.hasMore);
  };

  return { conversations, loadMore, hasMore };
};
```

### Messages

```ts
const useMessages = (conversationId: string) => {
  const [messages, setMessages] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  const loadOlder = async () => {
    if (!hasMore) return;
    const response = await api.getMessages(conversationId, { cursor, limit: 50 });
    setMessages(prev => [...response.data, ...prev]); // prepend
    setCursor(response.beforeCursor);
    setHasMore(response.hasMore);
  };

  return { messages, loadOlder, hasMore };
};
```

---

## Session Selection Rules

### Regras

1. **Última sessão selecionada** — reutilizar SOMENTE se ainda estiver WORKING
2. **Exatamente uma sessão WORKING** — pode selecionar conscientemente
3. **Ambiguidade ou nenhuma válida** — mostrar estado explícito

### PROIBIDO

```ts
// ❌ NUNCA
const session = workingSession || availableSessions[0];
```

### CORRETO

```ts
// ✅
const session = selectSession({
  lastSelected: lastSessionId,
  availableSessions,
  requireWorking: true
});

if (!session) {
  return <NoSessionAvailable />;
}
```

---

## Media Pipeline

### Fluxo

```
Mensagem recebida
  → media.state = 'pending'
  → GET /api/sessions/{session}/media?messageId=...
  → Se disponível: state = 'ready', serve arquivo
  → Se falhar: state = 'failed', mostra erro
```

### Não Depender De

- URLs temporárias do WhatsApp
- `pps.whatsapp.net`
- `fbcdn.net`

---

## Mobile

### Design

- TELA 1: Lista de conversas
- TELA 2: Chat ocupa praticamente toda a tela

### CSS

```css
.chat-container {
  height: 100dvh;
  padding-bottom: env(safe-area-inset-bottom);
}
```

### Touch Targets

- Mínimo 44x44px
- Sem sobreposição de elementos

---

## Estados Obrigatórios

Todo componente deve tratar:

| Estado | Tratamento |
|--------|------------|
| Loading | Skeleton ou spinner |
| Empty | Mensagem clara |
| Success | Renderizar dados |
| Partial | Dados incompletos, mostrar o que existe |
| Error | Mensagem + retry action |
| Offline | Indicador + modo offline |
| Permission denied | Ação para obter permissão |
| Disconnected | Estado da sessão |

---

## Referências

- `docs/architecture.md` — Arquitetura geral
- `docs/media-pipeline.md` — Pipeline de mídia
- `docs/refoundation/GOAL.md` — Princípios do Refoundation
