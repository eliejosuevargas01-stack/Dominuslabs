# Documentação do Componente OmnichannelView

## Visão Geral

O componente `OmnichannelView` é a página principal da interface de chat omnichannel, responsável por gerenciar conversas entre diferentes canais de comunicação (WhatsApp, CRM, etc.) em tempo real. Ele utiliza uma arquitetura React com TypeScript, integrando-se com APIs backend via Axios e WebSocket (SSE) para atualizações instantâneas.

### Tecnologias Principais
- **React** (18+) com hooks funcionais
- **TypeScript**
- **TailwindCSS** para estilização
- **Vite** como bundler/developer server
- **SSE (Server-Sent Events)** para atualizações em tempo real
- **Lucide React** para ícones
- **Sonner** para notificações

## Layout do Componente

```
┌────────────────────────────────────────────────────────┐
│           HEADER - Controles e Sessões                 │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │   Sidebar   │    │        Painel de Chat           │  │
│  │             │    │                                 │  │
│  │ Conversas   │    │  ┌─────────────────────────────┐  │  │
│  │ Contatos    │    │  │   Input de Mensagem         │  │  │
│  │             │    │  └─────────────────────────────┘  │  │
│  │             │    │  ┌─────────────────────────────┐  │  │
│  │             │    │  │    Mensagens do Chat        │  │  │
│  └─────────────┘    │  │                         │  │  │
│                     │  │      Scroll Auto          │  │  │
│                     │  │                         │  │  │
│                     │  │      Arrow Down Button    │  │  │
│                     │  └─────────────────────────────┘  │  │
│                     └─────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

## Estado React Principal

| Nome                 | Tipo                           | Função |
|----------------------|--------------------------------|--------|
| conversations        | Conversation[]                | Lista de conversas do usuário |
| chatMessages         | OmnichannelMessage[]          | Mensagens da conversa ativa |
| selectedChat         | Conversation \| null          | Conversa atualmente selecionada |
| selectedSession      | string                        | Filtro de sessão atual |
| activeSendSession    | string                        | Sessão ativa para envio de mensagens |
| isAtBottom           | boolean                       | Controla se chat está no final |
| loadingList          | boolean                       | Indicador de carregamento da lista |
| loadingHistory       | boolean                       | Indicador de carregamento do histórico |
| sending              | boolean                       | Indicador de envio de mensagem |
| searchTerm           | string                        | Termo de busca |
| messageInput         | string                        | Texto digitado no campo de entrada |

## Fluxo SSE - Mensagens em Tempo Real

1. **Conexão**: Componente se conecta a `GET /api/v1/webhooks/events/crm-chats` via `SSEClient`
2. **Recepção**: Backend envia eventos JSON em formato específico
3. **Processamento**:
   - Filtra por ação (`new_message`, `reload`, `session_disconnected`)
   - Identifica se o evento afeta o chat atual ou apenas a sidebar
   - Atualiza os estados correspondentes (`setChatMessages`, `setConversations`)
4. **Notificação sonora**: Toca som ao receber novas mensagens

## Pipeline de Deduplicação de Mensagens

**Três Camadas de Deduplicação**

1. **`knownMessageIds` (useRef)**:
   - Conjunto de `message_id` vistos
   - Previne replay de mensagens idênticas

2. **Handler SSE (dentro do evento `onMessage`)**:
   - Match exato de `message_id`
   - Para mensagens `is_from_me`: deduplica pelo conteúdo (compara `content` entre `temp_xxx` e o real)

3. **`sortedMessages` (useMemo)**:
   - Exclui mensagens de reação duplicadas
   - Deduplicação final por `message_id`
   - Deduplicação por conteúdo (`fromMe`) quando ambos usam o mesmo `content`

## Scroll Behavior

### **Auto Scroll**
- Ao abrir novo chat: scroll imediato para o final
- Quando nova mensagem chegou e usuário está no final: scroll suave automático

### **Botão de Scroll**
- Nova mensagem enquanto usuário leu para cima: mostra botão flutuante para baixo
- Comportamento controlado pelo `chatContainerRef` e `onScroll`

## Seleção de Sessão e Enviador

### **Filtro de Sessão**
- Botoes de sessão no header: clicando muda `selectedSession` e limpa `selectedChat`
- `filteredConversations` filtra conversas por `item.session_id === selectedSession`

### **Envio de Mensagem**
- Dropdown no header do chat ativo para escolher sessão de envio (`activeSendSession`)
- Lógica de prioridade:
  ```ts
  (activeSendSession && !== 'default' ? activeSendSession : null) || selectedChat.session_id || availableSessions[0].id
  ```

## Envio de Mensagens

1. **Estado Temporário**
   - Insere `tempMessage` com `message_id: temp_{timestamp}` no `chatMessages`
   - Status inicial: `'sending'`
2. **API Call**
   - Chama `sendOmnichannelMessage()` com payload
3. **Backend Resposta**
   - Retorna `realId` do message no backend (geralmente começa com `3EB`)
4. **Atualização Final**
   - SSE chega com ID real
   - Handler substitui `tempMessage` pela versão confirmada (real ID + status)

## Envio de Mídia

### **Tipos de Mídia suportados**
- Imagens
- Vídeos
- Áudio (gravado ao vivo)
- Documentos

### **Fluxo de Envio**
1. **Gravação de Áudio**
   - `startRecording()`: inicia gravação com `MediaRecorder`
   - `stopAndSendRecording()`: faz `blobToBase64()` e chama `sendOmnichannelMedia()`
2. **Upload de Arquivos**
   - `handleFileUpload()`: converte `Blob` para `base64` e envia
3. **Chamada API**
   - `sendOmnichannelMedia()`: para todos os tipos de mídia
   - Utiliza o mesmo pipeline de sessão de envio

## Tabela de Endpoints API

| Endpoint                                           | Método | Descrição                              |
|----------------------------------------------------|--------|----------------------------------------|
| `/api/v1/crm/messages/send`                       | POST   | Envia mensagem texto                   |
| `/api/v1/crm/messages/send-media`                 | POST   | Envia mídia (img, video, audio)        |
| `/api/v1/crm/conversations`                       | GET    | Busca lista de conversas               |
| `/api/v1/crm/chat-history/{jid}`                  | GET    | Busca histórico de chat                |
| `/api/v1/whatsapp/sessions`                       | GET    | Busca sessões WhatsApp disponíveis     |

---
**Status:** COMPLETED  
**Arquivo criado:** /home/eliezer/Escritorio/dominuslabs/docs/frontend-omnichannel.md