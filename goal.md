# 🎯 GOAL — Limpeza do Dominus sem regressão funcional

## 1. Objetivo

O Dominus atual no commit base `0fe7175b35d663bcb3c28cf03cfcb98afcbdf077` é a **fonte da verdade do contrato de integração** para IDPW e, futuramente, Whats API.

Este GOAL não autoriza redesenhar os fluxos que já funcionam. O trabalho no Dominus é exclusivamente:

- remover código legado, duplicado, morto ou de compatibilidade que não possui mais função real;
- reduzir caminhos alternativos para a mesma operação;
- consolidar chamadas M2M nos clientes internos já existentes;
- manter integralmente autenticação humana, tenant isolation, CRM, Omnichannel, SSE, pedidos, mídia, upload e demais comportamentos funcionais atuais;
- preservar o contrato criptográfico e HTTP já emitido pelo `IdentityClient` até que uma mudança futura seja explicitamente planejada em conjunto.

**Regra principal:** limpeza não pode alterar contrato externo, resposta funcional, permissões, ownership, fluxo de usuário ou comportamento válido já coberto por testes.

---

## 2. Contrato Dominus → IDPW congelado

O IDPW deve adaptar-se ao Dominus. O Dominus não deve ser modificado apenas para satisfazer uma implementação divergente do IDPW.

### Endpoint

`POST /v1/tokens`

### Payload lógico assinado

O `IdentityClient` gera exatamente:

- `aud`
- `tenant_id`
- `scope`
- `request_id`
- `timestamp`
- `nonce`
- `jti`

Todos devem ser obrigatórios, não vazios e semanticamente válidos.

### Assinatura do Dominus

O Dominus assina o JSON canônico do payload lógico:

- UTF-8;
- chaves ordenadas (`sort_keys=True`);
- separadores compactos equivalentes a `(',', ':')`;
- RSA PKCS#1 v1.5;
- SHA-256;
- assinatura codificada em Base64;
- campo declarativo `algorithm = "RS256"`.

A chave utilizada é `DOMINUS_PRIVATE_KEY`.

### Envelope lógico antes da criptografia

O objeto cifrado enviado ao IDPW contém:

- `aud`
- `tenant_id`
- `scope`
- `request_id`
- `timestamp`
- `nonce`
- `jti`
- `payload` — o payload lógico assinado acima;
- `signature` — assinatura Base64;
- `algorithm` — obrigatoriamente `RS256`.

Os valores duplicados no nível externo (`aud`, `tenant_id`, `scope`, `request_id`, `timestamp`, `nonce`, `jti`) devem ser idênticos aos valores dentro de `payload`.

### Criptografia Dominus → IDPW

O envelope lógico é cifrado uma única vez por `encrypt_payload(..., target="idpw")`:

- AES-256-GCM;
- chave AES aleatória de 32 bytes;
- IV de 16 bytes, conforme implementação atual do Dominus;
- authentication tag de 16 bytes;
- chave AES cifrada por RSA-OAEP;
- OAEP SHA-256;
- campos externos `_encrypted`, `encryptedKey`, `iv`, `authTag`, `payload` em Base64 conforme implementação atual.

Não pode haver dupla criptografia por `http_client` ou outro middleware.

### Headers Dominus → IDPW

Somente os headers HTTP normais necessários e:

- `Content-Type: application/json`
- `X-Request-ID: <request_id>`

`X-Request-ID` é correlação/observabilidade, nunca fonte de identidade ou autorização.

### Resposta esperada do IDPW

HTTP `200` deve retornar exclusivamente envelope criptografado para a chave pública do Dominus. Após descriptografar, o Dominus espera pelo menos:

- `access_token`
- `expires_in`

Resposta plaintext deve continuar sendo rejeitada fail-closed.

---

## 3. Escopos do Dominus — fonte da verdade nesta etapa

O contrato do IDPW deve aceitar somente os scopes efetivamente usados pelo Dominus nesta baseline:

- `whatsapp:sessions:read`
- `whatsapp:sessions:create`
- `whatsapp:sessions:write`
- `whatsapp:sessions:delete`
- `whatsapp:messages:send`

Não introduzir aliases CRUD (`read`, `write`, `update`, `delete`) nem wildcard administrativo.

Uma futura granularização de `sessions:write` em `connect`, `disconnect`, `webhooks:manage`, etc. deve ser um GOAL separado e coordenado. Não fazer essa mudança durante a limpeza.

---

## 4. Código que deve permanecer como autoridade

### `app/services/identity_client.py`

É o único cliente responsável por solicitar, receber, armazenar temporariamente e invalidar JWT M2M do IDPW.

Deve continuar sendo a autoridade para:

- cache M2M somente em memória;
- chave de cache `(tenant_id, scope, aud)`;
- renovação antes da expiração;
- `POST /v1/tokens`;
- criptografia de request;
- descriptografia de response;
- rejeição fail-closed de plaintext;
- invalidação após rejeição 401/403 por serviço downstream.

### `app/services/whatsapp_client.py`

Continua sendo o único cliente HTTP interno para Whats API. Nenhum endpoint/controller deve criar uma segunda implementação HTTP paralela.

### `app/services/whatsapp_service.py`

Deve ficar restrito a regras de negócio que realmente pertencem ao Dominus, principalmente:

- resolução de `tenant_id` do usuário;
- ownership positivo `user.tenant_id == whatsapp_account.tenant_id`;
- resolução de sessão pertencente ao tenant;
- composição de operações de negócio que delegam ao `WhatsAppClient`.

---

## 5. Limpeza obrigatória do Dominus

Antes de apagar qualquer símbolo, localizar consumidores reais no backend, frontend e testes. Remover somente depois de migrar ou confirmar ausência de consumidor.

### 5.1 Remover camada de compatibilidade M2M redundante

Eliminar `app/services/identity_service.py` se, após atualizar consumidores restantes, ele não possuir responsabilidade própria além de delegar ao `IdentityClient`.

Consumidores devem chamar `identity_client` diretamente quando isso não altera comportamento.

Não manter dois nomes para a mesma operação (`get_m2m_jwt`, `get_oauth_token`, etc.) sem necessidade funcional.

### 5.2 Limpar `whatsapp_service.py`

Remover funções de compatibilidade/no-op, incluindo quando confirmadas como legadas:

- `get_oauth_token()` se apenas delegar ao `IdentityClient`;
- `check_token_validity()` se não possuir regra de negócio própria;
- `invalidate_token(user_id)` no-op;
- imports e logs associados exclusivamente a essas camadas antigas.

Atualizar consumidores para a autoridade correta antes da remoção.

### 5.3 Remover integração Instagram residual do domínio WhatsApp

A Whats API atual já não possui integração Instagram funcional. Portanto, remover do Dominus, se não houver outro backend real responsável por ela:

- `WhatsAppClient.instagram_login()`;
- `WhatsAppClient.instagram_logout()`;
- rotas `/instagram/login`;
- rotas `/instagram/sessions/{username}/logout`;
- schemas/imports auxiliares exclusivos;
- testes que apenas perpetuam essas rotas mortas;
- referências de UI sem backend válido, quando existirem.

Essa remoção não deve afetar fluxos WhatsApp.

### 5.4 Remover aliases e helpers retrocompatíveis sem consumidor

Pesquisar e remover aliases explicitamente marcados como compatibilidade, wrappers de uma linha e helpers duplicados quando não houver consumidor real.

A remoção deve ser comprovada por busca estática + suíte de testes.

### 5.5 Limpar documentação e configuração obsoletas

Remover referências que indiquem como contrato atual qualquer mecanismo já abandonado, como:

- `WHATSAPP_MASTER_SECRET` como autenticação entre Dominus e Whats API;
- `X-Master-API-Key` em chamadas normais do Dominus;
- `x-session-token`;
- `x-tenant-id` como autoridade de tenant;
- tokens M2M enviados ao browser;
- IDPW remoto `/verify` ou introspecção obrigatória por request;
- autenticação local da Whats API;
- endpoints Instagram dentro da Whats API.

Manter documentação histórica apenas se claramente marcada como histórica e fora do caminho operacional.

### 5.6 Não armazenar credencial M2M fora do cache volátil

Garantir por busca e testes que JWT M2M do IDPW não seja persistido em:

- banco de dados;
- `WhatsappAccount`;
- `User`;
- localStorage/sessionStorage;
- payloads de frontend;
- logs;
- URLs/query strings.

---

## 6. Proibições desta etapa

Não fazer durante este GOAL:

- alterar o formato criptográfico Dominus → IDPW;
- trocar PKCS#1 v1.5 por RSA-PSS no Dominus;
- alterar IV do Dominus apenas para acompanhar o IDPW;
- alterar os scopes da baseline;
- introduzir mTLS;
- redesenhar Whats API;
- mudar rotas funcionais do Dominus que não sejam comprovadamente legadas;
- alterar formato de sessão ou migrations sem necessidade direta de remoção de legado;
- reintroduzir master keys ou credenciais compartilhadas;
- colocar JWT M2M no browser.

---

## 7. Testes obrigatórios de não regressão

### Contrato IDPW do lado Dominus

Manter/adicionar testes que provem:

1. `IdentityClient` envia exatamente uma camada de criptografia;
2. o envelope descriptografado possui exatamente os campos previstos neste GOAL;
3. `signature` valida sobre o JSON canônico de `payload` com RSA PKCS#1 v1.5 + SHA-256;
4. `algorithm == "RS256"`;
5. `request_id`, `timestamp`, `nonce` e `jti` existem e não são vazios;
6. resposta plaintext do IDPW é rejeitada;
7. ausência das chaves obrigatórias falha fechado;
8. `access_token` nunca é persistido fora do cache em memória.

### Regressão funcional Dominus

Devem continuar verdes:

- backend tests;
- security tests/Bandit existentes;
- frontend lint;
- frontend tests;
- frontend build;
- tenant ownership tests;
- mídia/avatar privados;
- CRM/webhooks;
- SSE;
- Order Manager;
- Omnichannel;
- autenticação e refresh humanos.

### Teste contra legado

Adicionar uma checagem automatizada ou testes específicos para impedir reintrodução de credenciais/headers proibidos no caminho Dominus → Whats API e M2M → frontend.

---

## 8. Critério de conclusão

Este GOAL só está concluído quando:

- o comportamento funcional da baseline permanece igual;
- os testes anteriores continuam verdes;
- nenhum consumidor depende das camadas removidas;
- existe um único `IdentityClient` M2M;
- existe um único `WhatsAppClient` interno;
- não existe integração Instagram morta no domínio WhatsApp;
- não existem wrappers/no-ops de compatibilidade sem consumidor;
- não há token M2M persistido ou exposto ao browser;
- o contrato Dominus → IDPW descrito neste arquivo possui teste determinístico reproduzível;
- o commit final contém principalmente deleções/simplificações, exceto pelos testes necessários para comprovar ausência de regressão.
