# Pipeline de Mídia

## Visão Geral

```
┌─────────────┐    ┌───────────┐    ┌─────────────┐    ┌────────────┐    ┌──────────────┐
│  WhatsApp   │───▶│ Download  │───▶│   Disco     │───▶│ Webhook    │───▶│   n8n        │
└─────────────┘    └───────────┘    └─────────────┘    └────────────┘    └──────────────┘
                                                                 ▲
                                                                 │
                                                                 │
                                                       ┌─────────┴─────────┐
                                                       │   Banco de Dados  │
                                                       └───────────────────┘
                                                                 ▲
                                                                 │
                                                                 │
                                                       ┌─────────┴─────────┐
                                                       │   Frontend        │
                                                       └───────────────────┘
```

## Fluxo de Recebimento

1. **Recebimento**: O Baileys processa a mensagem com mídia usando `media.download`
2. **Processamento**: `handleMessagesUpsert` detecta `storedMessage.media.download`
3. **Download**: A função `resolveMessageMedia` chama `downloadMediaMessage` (Baileys) para obter o buffer
4. **Armazenamento**: `cacheMediaBuffer` salva no diretório `/app/data/media/SESSIONID/FILENAME`
5. **Caminho**: `message.media.cachePath` aponta para o caminho relativo do arquivo salvo

## Formato do Nome de Arquivo

Formato: `JIDCLEAN_TIMESTAMP.ext`

Exemplo:
- JID: `178189703839815@lid`
- Timestamp: `1790113823`
- Arquivo gerado: `178189703839815_lid_1790113823.jpg`

> JIDCLEAN é o JID com `@` substituído por `_`, `:` por `_`, `.` por `_`, etc.

## Volume Persistente

Estrutura de diretórios:
```
/app/data/media/
├── SESSIONID1/
│   ├── FILENAME1.ext
│   └── ...
└── SESSIONID2/
    ├── FILENAME2.ext
    └── ...
```

## Endpoint de Serviço de Mídia

Endpoint: `GET /api/sessions/SESSIONID/media?messageId=MESSAGEID`

Validações de segurança:
- Validação do `cachePath` dentro do diretório do tenant
- Streaming do arquivo com o `Content-Type` correto
- Proteção contra navegação fora do diretório permitido

## Campo `media.url` no Payload do Webhook

O campo `media.url` no payload do webhook contém o endpoint de acesso à mídia:
`/api/sessions/SESSIONID/media?messageId=MESSAGEID`

## Problemas Atuais

### T2 - n8n salva JSON ao invés de URL

**Problema:** O n8n salva o resultado de `JSON.stringify(media)` em vez de apenas `media.url`

**Solução Prevista:** Ajustar o fluxo do n8n para extrair apenas o `media.url` antes de salvar

### T3 - Frontend utiliza media_url incorretamente

**Problema:** Frontend espera URL em `messages.media_url` mas recebe JSON String

**Solução Prevista:** Alterar o frontend para fazer `JSON.parse(messages.media_url)` antes de usar

## Como o Frontend Exibe Mídias

O frontend utiliza o campo `media_url` como uma URL válida para carregar a mídia. No entanto, atualmente está recebendo um JSON string, o que impede o carregamento correto.

## Tipos Suportados

- image (imagem)
- video (vídeo)
- audio (áudio)
- document (documento)
- sticker (adesivo)

## Limites

- Tamanho máximo por arquivo: 15MB
