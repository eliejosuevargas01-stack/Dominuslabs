# Guia de Integração: Dominus Backend ⇄ Sistemas Externos

Este documento detalha como os sistemas externos devem se comunicar com o backend do Dominus para garantir latência e fricção mínimas, de acordo com as regras de negócio estabelecidas.

## 1. Identity Worker (IDPW)
**Objetivo:** Prover autenticação e provisionamento de sessões M2M (Machine-to-Machine) via JWT para instâncias do sistema.

### Provisionamento e Autenticação
- **Endpoint:** `/api/v1/auth/provision` (ou no Identity Worker equivalente)
- **Fluxo:**
  1. O backend Dominus envia uma solicitação assinada.
  2. O IDPW responde com um `access_token` JWT contendo as claims necessárias (`tenant_id`, `scope`).
  3. O backend valida a assinatura e expiração sem chamadas síncronas extras.
- **Payload Esperado (JWT):**
  ```json
  {
    "iss": "https://identity.dominus.online",
    "aud": "whatsapp-api",
    "sub": "dominus-prod",
    "tenant_id": "tenant_123",
    "scope": "whatsapp:messages:send",
    "exp": 1900000000
  }
  ```

## 2. N8N (Automação de Fluxos de Trabalho)
**Objetivo:** Orquestrar integrações de CRM, notificações e campanhas.

### Webhooks de Recepção (Inbound)
- **Endpoint:** `/webhooks/events/crm-chats` (e similares)
- **Cabeçalhos Exigidos:** `X-Master-API-Key` ou assinaturas HMAC configuradas.
- **Payload Esperado (Exemplo de Mensagem Recebida):**
  O N8N deve enviar dados estritos que correspondam aos schemas Pydantic, garantindo consistência com o frontend.
  ```json
  {
    "event": "new_message",
    "lead_id": "lead_123",
    "message": {
      "id": "msg_456",
      "sender": "client",
      "content": "Gostaria de mais informações",
      "timestamp": "2023-10-25T12:00:00Z"
    }
  }
  ```

## 3. WhatsApp API
**Objetivo:** Envio e recebimento de mensagens e mídias no modelo Omnichannel.

### Padrão de Comunicação
- **Envio de Mensagem:** `/api/v1/crm/messages/send`
  O backend atua como proxy, repassando o payload formatado corretamente para a API do WhatsApp.
- **Tratamento de Mídias:**
  As mídias são enviadas via base64 ou URL (dependendo do suporte configurado), utilizando o payload `OmnichannelMessage` validado em ambos os lados.

## Boas Práticas para Integração
- **Latência:** Chamadas externas do FastAPI devem ser feitas via `httpx.AsyncClient` para não bloquear o event loop.
- **Tratamento de Erros:** O backend deve sempre retornar JSONs claros para erros, que serão renderizados de forma amigável no frontend (via `sonner` toast).
- **Consistência:** Os payloads de resposta do backend (`schemas/crm.py`) mapeiam exatamente os tipos TypeScript do frontend. Não introduza novos campos no fluxo do N8N ou WhatsApp sem antes atualizar a interface TypeScript e o schema Pydantic.
