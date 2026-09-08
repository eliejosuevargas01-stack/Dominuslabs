# Plano de implementação — Limpeza do Dominus sem regressão

## Contratos congelados

- `IdentityClient` continua emitindo `POST /v1/tokens` com uma única criptografia híbrida e envelope lógico assinado por RSA PKCS#1 v1.5 + SHA-256 (`RS256`).
- `WhatsAppClient` continua emitindo apenas Bearer M2M, `X-Request-ID` e `Idempotency-Key` quando aplicável, invalidando o cache após 401/403.
- Autenticação humana, permissões, ownership, CRM/n8n, Omnichannel, SSE, pedidos, mídia, upload e schemas consumidos permanecem funcionalmente idênticos.

## Implementação

1. Substituir imports/chamadas delegadas por suas autoridades atuais e então remover `identity_service.py` e os no-ops de `whatsapp_service.py`.
2. Remover o proxy Instagram inexistente de ponta a ponta: métodos do cliente, rotas FastAPI, funções da API frontend, estados/handlers/modal/cartão da tela de conexões e testes exclusivos dessas rotas.
3. Remover wrappers sem responsabilidade própria comprovadamente internos, migrando previamente seus consumidores para os símbolos canônicos. Não tocar em compatibilidade ainda consumida ou cujo produtor externo não possa ser provado obsoleto.
4. Atualizar `INTEGRATION_GUIDE.md` para o contrato atual e manter referências a mecanismos proibidos apenas em deny-lists/testes negativos, nunca como instrução operacional.

## Interfaces e limites

- Interfaces removidas: módulo interno `app.services.identity_service`; helpers internos M2M de `whatsapp_service`; rotas `/api/v1/whatsapp/instagram/login` e `/api/v1/whatsapp/instagram/sessions/{username}/logout`; helpers frontend correspondentes.
- Nenhuma rota WhatsApp funcional, schema de banco, migration, scope, formato criptográfico ou resposta válida será adicionada ou alterada.
- O webhook `/api/v1/webhooks/inbound/instagram`, os campos Instagram de CRM e links sociais não fazem parte do proxy morto e serão preservados.
- `x-tenant-id` dos produtos e autenticação especial de pedidos estão fora do caminho Dominus→Whats API/M2M e não serão redesenhados nesta limpeza.

## Testes e aceite

- Teste do `IdentityClient` descriptografa o request uma vez, compara conjuntos exatos de campos interno/externo, verifica igualdade dos duplicados e valida a assinatura canônica com a chave pública de teste.
- Testes cobrem campos obrigatórios não vazios, `algorithm == "RS256"`, headers exatos, rejeição de resposta plaintext/incompleta, cache apenas em memória e invalidação em 401/403.
- Testes/checagens impedem reintrodução das rotas Instagram mortas, do módulo delegador, de headers proibidos no `WhatsAppClient` e de credencial M2M no frontend.
- Aceite final: pytest completo, Bandit `-ll -ii`, ESLint, Vitest e build verdes; busca estática sem consumidores quebrados; Code Review sem P0/P1; QA Jules concluído com evidências; nenhum merge/deploy.
