# CONTRACTS — Integração Open Delivery Multi-Tenant

> Regras invioláveis durante toda a implementação. Qualquer task que viole um contrato deve ser rejeitada na auditoria.

---

## 1. Isolamento Multi-Tenant

- **TODA** query ao banco filtra por `tenant_id`.
- **TODA** credencial pertence a exatamente um tenant.
- Um tenant **nunca** vê, modifica ou recebe dados de outro tenant.
- O `tenant_id` vem **exclusivamente** do JWT do operador (`get_operator_tenant_id`) ou do `merchant_id` mapeado no webhook da plataforma.
- Nunca aceitar `tenant_id` de query string, body ou header arbitrário.

## 2. Segurança de Credenciais

- Credenciais de plataformas externas (clientId, clientSecret, tokens) são **encriptadas at-rest** no banco usando primitivas derivadas do crypto.py.
- Credenciais **nunca** aparecem em:
  - Respostas de API (GET /integrations retorna metadata, não secrets)
  - Logs (nem em nível DEBUG)
  - Frontend (localStorage, state, props, DOM)
  - Commits ou arquivos não-encriptados
  - Mensagens de erro retornadas ao cliente
- `DOMINUS_PRIVATE_KEY` continua sendo a raiz de confiança. Sem ela → fail-closed.

## 3. Compatibilidade com o Order Manager existente

- Pedidos de plataformas externas **usam o mesmo `OrderManagerOrder`** — não criar tabela paralela.
- Os campos `source_platform` e `external_order_id` distinguem a origem.
- `broadcast()` SSE/WS funciona **identicamente** para pedidos internos e externos.
- Alarmes TTS disparam para pedidos externos exatamente como para internos.
- O operador **não precisa saber** se o pedido veio do WhatsApp ou do Pedidos10 — o fluxo PDV é idêntico.
- `handleAccept`, `handleReject`, `handleStatusChange` no frontend **não mudam**. O backend decide internamente se precisa notificar n8n ou a plataforma externa.

## 4. Não modificar componentes existentes (exceto onde explicitado)

- **IdentityClient**: não tocar. Criar `PlatformTokenManager` separado inspirado nele.
- **WhatsAppClient**: não tocar.
- **N8NService**: não tocar.
- **Workflows n8n**: não tocar (Dominus AI, Buffer, CRM, Respostas).
- **Endpoints existentes de orders.py**: modificar apenas para adicionar hook de status sync outbound nos endpoints de status change. Não alterar a lógica de recebimento n8n.
- **crypto.py**: pode adicionar funções de encriptação at-rest, mas **não alterar** as funções de encriptação em trânsito existentes.

## 5. Open Delivery Protocol Compliance

- Implementar endpoints conforme **Open Delivery API v1.7.x** (abrasel-nacional/opendelivery).
- Auth entre Ordering Application e Software Service usa **OAuth2 client_credentials**.
- Credenciais são **por merchant** (por tenant), não por software.
- O DominusLabs atua como **Software Service** no protocolo Open Delivery.
- Status transitions seguem o mapeamento definido no plan.md — não inventar transições novas.

## 6. Experiência do Tenant

- O tenant **não é desenvolvedor**.
- A integração é feita por **interface gráfica** (botão "Conectar" + campo "Código da loja" ou redirect OAuth).
- O tenant **nunca** precisa lidar com: clientId, clientSecret, baseURL, webhook URL, tokens, headers, JSON ou documentação de API.
- Mensagens de erro para o tenant devem ser em **português**, claras e acionáveis ("Não foi possível conectar ao Pedidos10. Verifique se o código da loja está correto.").

## 7. Fail-Closed

- Sem credencial de plataforma → pedido não é aceito dessa plataforma (mas o PDV continua funcionando para outras fontes).
- Token OAuth2 expirado e não-renovável → log error + desativar integração + notificar tenant.
- Webhook recebido com assinatura inválida → rejeitar silenciosamente (401), nunca processar.
- Plataforma fora do ar → retry com backoff. Após esgotamento, marcar `last_error` na integração. Não bloquear o PDV.

## 8. Testes

- **TODA** task deve manter os 17 testes existentes passando.
- **TODA** task deve adicionar testes unitários para o código novo.
- TypeScript (`tsc --noEmit`) deve compilar sem erros após cada task.
- Testes de integração com mock (httpx_mock) para chamadas a plataformas externas.
- Nenhum teste faz chamadas reais a APIs externas — sempre mock.

## 9. Dados

- `Product` e `CompanySetting` são **read-only** do ponto de vista da integração Open Delivery. A plataforma lê o cardápio, mas não escreve nele.
- `OrderManagerOrder` é writable pela integração apenas para **criar pedidos** (inbound) e **atualizar status via operador** (outbound). A plataforma não altera pedidos diretamente no DominusLabs.
- Nenhuma migration será executada automaticamente. Migrations requerem aprovação explícita e task separada.

## 10. Rollback

- Cada task deve ser revertível independentemente (git revert do commit).
- Se a integração Open Delivery apresentar problemas em produção, desativar (`is_active=False`) deve ser suficiente para voltar ao comportamento anterior — sem necessidade de rollback de código.
- O flag `is_active` na `TenantPlatformIntegration` é o circuit breaker da integração.
