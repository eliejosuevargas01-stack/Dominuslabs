# Tasks — Limpeza de legado sem regressão

## 1. Baseline e inventário

- Registrar consumidores reais das camadas candidatas no backend, frontend e testes.
- Executar pytest, Bandit, lint, Vitest e build antes das mudanças para separar falhas preexistentes de regressões.

## 2. Consolidar o fluxo M2M

- Migrar o único consumidor de `identity_service.py` para `identity_client` e remover a camada delegadora.
- Remover `get_oauth_token`, `check_token_validity` e `invalidate_token` de `whatsapp_service.py`, junto com imports sem uso.
- Manter `IdentityClient` como única autoridade de token e `WhatsAppClient` como único cliente interno da Whats API.

## 3. Remover Instagram residual do domínio WhatsApp

- Excluir os métodos `instagram_login`/`instagram_logout`, as duas rotas proxy e seus testes de perpetuação.
- Excluir os helpers e a interface de conexão Instagram em `ConnectionsView`, preservando campos de lead, webhook inbound n8n e demais recursos CRM/Instagram independentes.

## 4. Remover compatibilidade comprovadamente inútil

- Eliminar aliases/wrappers de uma linha somente após migrar consumidores internos: factory HTTP compatível, permissões de projeto, alias preventivo de refresh e alias não usado de histórico n8n.
- Preservar aliases de permissões, schemas e payloads que possuem consumidores atuais ou contrato externo não comprovadamente obsoleto.

## 5. Congelar contrato e documentação

- Tornar determinísticos os testes do envelope assinado/cifrado do `IdentityClient`, incluindo campos exatos, assinatura RS256, camada única, headers, resposta cifrada e falha fechada.
- Impedir reintrodução de headers/credenciais legados no transporte Whats API e exposição de M2M ao frontend.
- Corrigir o guia operacional para `POST /v1/tokens` e o contrato descrito no `goal.md`.

## 6. Gates de entrega

- Reexecutar toda a matriz local e buscas estáticas; o diff deve ser predominantemente deleções/simplificações.
- Commitar e enviar somente arquivos do GOAL, executar Code Review no SHA exato e QA Jules na branch.
- Corrigir bloqueadores e repetir os gates. Não fazer merge em `main` nem deploy.
