# Guia de Integração: Dominus Backend ⇄ Sistemas Externos

Este guia descreve os contratos operacionais atuais. O backend é a fronteira de confiança para identidade humana, tenant e credenciais de serviço; o frontend nunca recebe credenciais M2M.

## 1. Identity Worker (IDPW)

**Objetivo:** emitir JWT M2M de curta duração para as chamadas internas do Dominus à Whats API.

### Solicitação de token

- **Endpoint do IDPW:** `POST /v1/tokens`.
- **Cliente responsável:** somente `app/services/identity_client.py`.
- **Headers definidos pela aplicação:** somente `Content-Type: application/json` e `X-Request-ID: <request_id>`; o cliente HTTP acrescenta os headers normais de transporte.
- **Cache:** exclusivamente em memória, indexado por `(tenant_id, scope, aud)`; no executor HTTP comum, uma rejeição `401` ou `403` da Whats API invalida a entrada correspondente.

O payload lógico assinado contém exatamente:

```json
{
  "aud": "whatsapp-api",
  "tenant_id": "tenant_123",
  "scope": "whatsapp:messages:send",
  "request_id": "<uuid>",
  "timestamp": 1900000000,
  "nonce": "<hex-aleatorio>",
  "jti": "<uuid>"
}
```

O Dominus serializa esse objeto em UTF-8 com chaves ordenadas e separadores compactos, assina-o com `DOMINUS_PRIVATE_KEY` usando RSA PKCS#1 v1.5 e SHA-256 e codifica a assinatura em Base64. O envelope lógico contém os sete campos acima, cópias idênticas em `payload`, mais `signature` e `algorithm: "RS256"`.

O envelope é cifrado uma única vez para o IDPW por criptografia híbrida AES-256-GCM + RSA-OAEP/SHA-256. O transporte recebe `_encrypted: true` e os campos `encryptedKey`, `iv`, `authTag` e `payload` em Base64. Uma resposta HTTP `200` também deve ser cifrada para a chave pública do Dominus e, após descriptografada, conter `access_token` não vazio e `expires_in` inteiro positivo. Plaintext, campo ausente ou validade inválida são rejeitados sem fallback.

### Scopes aceitos nesta integração

- `whatsapp:sessions:read`
- `whatsapp:sessions:create`
- `whatsapp:sessions:write`
- `whatsapp:sessions:delete`
- `whatsapp:messages:send`

## 2. Whats API

**Objetivo:** gerenciar sessões WhatsApp e enviar/receber mensagens e mídias no modelo Omnichannel.

- Todo tráfego interno passa por `app/services/whatsapp_client.py`.
- O backend resolve e valida positivamente o `tenant_id` e o ownership da sessão antes de delegar a operação.
- As chamadas usam `Authorization: Bearer <JWT_M2M>` e `X-Request-ID`; operações mutáveis também usam `Idempotency-Key`.
- Corpos JSON são cifrados uma vez para a Whats API. O JWT M2M não é salvo em banco, entidade, log, URL ou storage do browser.
- Rotas funcionais do Dominus incluem `/api/v1/whatsapp/sessions` e `/api/v1/whatsapp/sessions/{session_id}/messages/send`; o CRM também compõe envios por `/api/v1/crm/messages/send`.

## 3. n8n (automação de fluxos)

**Objetivo:** orquestrar integrações de CRM, notificações e campanhas.

Webhooks inbound exigem `X-N8N-Signature`, `X-N8N-Timestamp` e `X-N8N-Event-Id`. A assinatura é o HMAC-SHA256 de `timestamp.event_id.body`, usando o corpo bruto. Timestamp fora da tolerância, evento repetido, segredo bruto, credencial em query string ou JWT de usuário humano são rejeitados.

Exemplo de corpo para `POST /api/v1/webhooks/inbound/instagram`:

```json
{
  "tenant_id": "tenant_123",
  "lead_id": "lead_123",
  "sender": "lead",
  "message": "Gostaria de mais informações"
}
```

## Boas práticas

- Faça chamadas externas de forma assíncrona e mantenha timeout explícito.
- Preserve `X-Request-ID` somente para correlação; ele não concede identidade, tenant ou autorização.
- Trate erros de serviços sem expor tokens, chaves ou payloads sensíveis.
- Mantenha schemas Pydantic e tipos TypeScript sincronizados antes de alterar payloads funcionais.
- Mudanças em criptografia, scopes ou rotas válidas exigem um objetivo coordenado separado; não use mecanismos de compatibilidade como fallback.
