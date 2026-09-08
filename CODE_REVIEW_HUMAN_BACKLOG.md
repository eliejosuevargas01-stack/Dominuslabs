# Code Review Human Backlog

Itens e melhorias não-bloqueantes apontados pelo Code Review (Dominus-MCP) para acompanhamento técnico futuro:

## 1. Tipagem Estrita TypeScript e Redução de `any`
- **Arquivos:** `src/components/GlobalOrderNotification.tsx`, `src/pages/OmnichannelView.tsx`
- **Evidência:** Uso de `any` em estados de listas como conversas e contatos (`useState<any[]>`), em referências de timer (`recordingTimerRef = useRef<any>(null)`), e coerção de tipo como `(oscillatorRef.current as any)._pulseInterval`.
- **Ação Sugerida:** Declarar interfaces formais explícitas (`IContact`, `IMessage`, `IOmniSession`) e criar refs dedicadas para timers e osciladores em substituição à tipagem flexível.
- **Prioridade:** P2 (Não bloqueante para deploy).

## 2. Assinatura dos Webhooks de GitHub e Deploy
- **Fonte:** Code Review Dominus-MCP do commit `1fd515a5f38d80c694e6938d7c1265548ca60ef1`.
- **Arquivos:** `project-hub/backend/app/api/endpoints/webhooks.py` (`/github/{public_token}`, `/github` e `/deploy`).
- **Evidência:** As rotas processam payloads externos sem validar uma assinatura criptográfica do provedor.
- **Ação sugerida:** Definir segredos por integração e validar HMAC (por exemplo, `X-Hub-Signature-256` do GitHub) antes de processar ou persistir o payload.
- **Prioridade:** Follow-up humano não bloqueante; requer provisionamento seguro dos segredos dos provedores.

## 3. Restabelecer a asserção interna do webhook GitHub
- **Fonte:** Code Review Dominus-MCP do commit `57624bbf`.
- **Arquivo:** `project-hub/backend/tests/test_webhooks.py` (teste `test_github_webhook`).
- **Evidência:** A asserção `mock_process.assert_called_once()` permanece comentada após um problema anterior de injeção de mock.
- **Ação sugerida:** Corrigir o ponto de patch do mock e reativar a asserção para validar o efeito interno, não apenas a resposta HTTP.
- **Prioridade:** Follow-up humano não bloqueante; não há defeito funcional confirmado na rota.

## 4. Remover import redundante de JSON no notificador CRM
- **Fonte:** Re-revisão Dominus-MCP do commit `943e59e4`.
- **Arquivo:** `project-hub/backend/app/api/endpoints/webhooks.py` (`notify_crm_chat_listeners`).
- **Evidência:** A função possui `import json` local embora o módulo já seja importado no topo do arquivo.
- **Ação sugerida:** Remover o import local em uma limpeza futura, mantendo a importação de módulo única.
- **Prioridade:** Follow-up humano não bloqueante; sem impacto funcional ou de segurança.

## 5. Invalidar cache M2M quando o proxy de mídia receber 401/403
- **Fonte:** revisão local de segurança do GOAL de limpeza legada.
- **Arquivo:** `project-hub/backend/app/services/whatsapp_client.py` (`get_session_media`).
- **Evidência:** o caminho de mídia fecha a resposta e devolve erro, mas não chama `identity_client.invalidate_token()` como o executor HTTP comum faz após rejeição `401` ou `403`.
- **Ação sugerida:** alinhar o caminho de streaming à política de invalidação em um GOAL funcional próprio, com teste de regressão específico.
- **Prioridade:** P2 preexistente e fora do escopo desta limpeza; não bloqueia este GOAL.

## 6. Sanitizar corpo textual de erros do IDPW antes de registrar ou propagar
- **Fonte:** revisão local de segurança do GOAL de limpeza legada.
- **Arquivo:** `project-hub/backend/app/services/identity_client.py` (tratamento de `401`/`403`).
- **Evidência:** `resp.text` é registrado e incluído no detalhe devolvido; um IDPW divergente poderia ecoar material sensível no corpo de erro.
- **Ação sugerida:** substituir o corpo bruto por uma mensagem sanitizada e manter apenas status/request ID em logs, coordenando a alteração de contrato em tarefa própria.
- **Prioridade:** P2 de defesa em profundidade, preexistente e fora do escopo desta limpeza; não bloqueia este GOAL.

## 7. Fechar o cliente HTTP ao concluir streaming de mídia
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d` (trecho comprovadamente idêntico ao pai).
- **Arquivo:** `project-hub/backend/app/services/whatsapp_client.py` (`get_session_media`).
- **Evidência:** a resposta em streaming é fechada pelo controller, mas o `httpx.AsyncClient` criado no service não tem ciclo de vida explícito no caminho de sucesso.
- **Ação sugerida:** encapsular client e response em gerador/context manager com fechamento garantido, acompanhado por teste de streaming e desconexão do consumidor.
- **Prioridade:** dívida preexistente potencialmente relevante; tratar em GOAL funcional próprio para não arriscar o fluxo de mídia congelado nesta limpeza.

## 8. Avaliar pooling para clientes HTTP internos
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivos:** `project-hub/backend/app/core/http_client.py`, `app/services/identity_client.py` e `app/services/whatsapp_client.py`.
- **Evidência:** cada operação cria e fecha um `AsyncClient`, sem reaproveitar pool TCP/TLS.
- **Ação sugerida:** medir carga e, se necessário, gerir um cliente compartilhado no lifespan da aplicação, preservando timeouts e isolamento.
- **Prioridade:** P2 de desempenho preexistente; exige desenho e testes separados.

## 9. Uniformizar respostas de sessão inexistente e cross-tenant
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivo:** `project-hub/backend/app/services/whatsapp_service.py`.
- **Evidência:** a mensagem de `403` diferencia sessão pertencente a outro tenant de sessão inexistente, podendo funcionar como sinal de enumeração.
- **Ação sugerida:** avaliar resposta externa uniforme sem perder auditoria interna, com testes de ownership e compatibilidade do frontend.
- **Prioridade:** P2 de hardening preexistente; fora da remoção de legado.

## 10. Remover rewrite de protocolo acoplado à porta 3000
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivo:** `project-hub/backend/app/services/whatsapp_client.py` (`base_url`).
- **Evidência:** URLs `http://...:3000` são convertidas automaticamente para HTTPS, inclusive em mocks e ambientes locais.
- **Ação sugerida:** mover a decisão de protocolo integralmente para `WHATSAPP_API_URL`, após validar todos os ambientes.
- **Prioridade:** P2 preexistente de configuração; requer tarefa coordenada.

## 11. Mover imports locais de `asyncio` para o topo
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivo:** `project-hub/backend/app/services/identity_client.py`.
- **Evidência:** os caminhos de retry importam `asyncio` dentro dos blocos condicionais.
- **Ação sugerida:** consolidar o import em uma limpeza futura sem alterar retry/backoff.
- **Prioridade:** P3 preexistente de legibilidade.

## 12. Validar padding Base64URL da autenticação humana
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivo:** `project-hub/backend/app/core/auth.py` (`base64url_decode`).
- **Evidência:** o cálculo atual pode acrescentar quatro `=` quando o tamanho já é múltiplo de quatro; o comportamento tolerado pelo decoder precisa ser comprovado para todos os payloads.
- **Ação sugerida:** adicionar casos determinísticos e, se houver falha, usar `((4 - len(data) % 4) % 4)` em GOAL próprio.
- **Prioridade:** investigação preexistente; não é regressão deste commit.

## 13. Consolidar parsing de Bearer nos proxies de avatar e mídia
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivos:** `project-hub/backend/app/api/endpoints/crm.py` e `app/api/endpoints/whatsapp.py`.
- **Evidência:** rotas de mídia/avatar repetem extração e decode manual do header em vez de uma dependência comum.
- **Ação sugerida:** desenhar uma dependência única mantendo exatamente os formatos e respostas atuais, com regressão de autenticação/query-string.
- **Prioridade:** P2 preexistente; refatoração funcional fora deste GOAL.

## 14. Auditar isolamento de tenant no Project Hub
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivos:** `project-hub/backend/app/api/endpoints/projects.py` e repositórios relacionados.
- **Evidência:** algumas listagens não recebem `tenant_id` explicitamente; não foi confirmado se o domínio é global por desenho ou se o filtro ocorre em outra camada.
- **Ação sugerida:** documentar a regra de negócio e criar testes multi-tenant antes de qualquer alteração.
- **Prioridade:** auditoria humana preexistente, sem vulnerabilidade confirmada neste review.

## 15. Validar conteúdo real nos uploads gerais
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivo:** `project-hub/backend/app/api/endpoints/uploads.py`.
- **Evidência:** a classificação de imagens/vídeos usa o `Content-Type` informado pelo cliente; o fluxo específico de mídia de produto já possui validações mais fortes.
- **Ação sugerida:** validar magic number e limites no endpoint geral, com matriz de formatos e arquivos adulterados.
- **Prioridade:** P2 de hardening preexistente; requer mudança funcional separada.

## 16. Remover contatos conhecidos hardcoded do serviço n8n
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivo:** `project-hub/backend/app/services/n8n_service.py` (`KNOWN_CONTACT_NAMES`).
- **Evidência:** o código contém JIDs/nomes conhecidos dependentes de ambiente.
- **Ação sugerida:** confirmar consumidores e migrar para configuração ou banco antes da remoção.
- **Prioridade:** follow-up humano preexistente; não remover sem prova de compatibilidade.

## 17. Reduzir docstrings boilerplate no backend
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivos:** backend, com alta incidência em `project-hub/backend/app/services/n8n_service.py`.
- **Evidência:** várias docstrings genéricas repetem o nome da função sem explicar regra ou contrato.
- **Ação sugerida:** substituir por documentação útil ou remover em lotes pequenos, sem misturar com mudanças funcionais.
- **Prioridade:** P3 de manutenibilidade preexistente.

## 18. Desacoplar notificações visuais da camada de serviço frontend
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d` (trecho preexistente).
- **Arquivo:** `src/services/api.ts` (`getUserRole`).
- **Evidência:** o helper de leitura do token dispara `toast.error` diretamente no tratamento de falha, acoplando utilitário de serviço à apresentação.
- **Ação sugerida:** retornar erro tipado ou estado neutro e deixar o componente consumidor decidir a notificação, após mapear todos os consumidores.
- **Prioridade:** P3 de separação de responsabilidades; fora da remoção de legado.

## 19. Padronizar blocos de erro na tela de conexões
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d` (trechos preexistentes).
- **Arquivo:** `src/pages/ConnectionsView.tsx`.
- **Evidência:** alguns `catch` mantêm `console.error` e `toast.error` na mesma linha, reduzindo legibilidade e dificultando regras automáticas de estilo.
- **Ação sugerida:** separar as instruções e padronizar mensagens em uma limpeza frontend dedicada, sem mudar o tratamento funcional.
- **Prioridade:** P3 de legibilidade; não bloqueante.

## 20. Estender tipagem estrita ao fluxo de conexões
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d` (tipagem preexistente).
- **Arquivos:** `src/pages/ConnectionsView.tsx` e `src/services/api.ts`.
- **Evidência:** respostas de sessão, erros, timer e payload de settings ainda usam `any` em pontos do fluxo preservado de WhatsApp.
- **Ação sugerida:** criar tipos de resposta/payload e usar `ReturnType<typeof setInterval>` e `unknown` para erros, acompanhados pelos testes atuais da tela.
- **Prioridade:** P2/P3 de manutenibilidade; fora deste GOAL.

## 21. Formalizar se respostas da WhatsApp API exigem envelope criptografado
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivos:** `project-hub/backend/app/services/whatsapp_client.py` e `project-hub/backend/tests/test_e2e_jwt_flow.py`.
- **Evidência:** o cliente suporta descriptografar respostas marcadas com `_encrypted`, enquanto o cenário E2E de envio também aceita a resposta atual em JSON simples; o GOAL congela criptografia obrigatória para IDPW, mas não define essa obrigatoriedade para respostas da WhatsApp API.
- **Ação sugerida:** confirmar o contrato upstream e, somente se o envelope for obrigatório, adotar rejeição fail-closed e ajustar mocks/testes em uma tarefa funcional própria.
- **Prioridade:** investigação de segurança/contrato preexistente; nenhuma regressão foi confirmada nesta limpeza.

## 22. Avaliar normalização única dos identificadores de sessão WhatsApp
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivos:** `project-hub/backend/app/services/whatsapp_service.py` e `project-hub/backend/tests/test_whatsapp.py`.
- **Evidência:** a sincronização preservada aceita e persiste as variantes com slug e nome bruto da mesma sessão para compatibilidade de roteamento.
- **Ação sugerida:** medir duplicação real e, se aplicável, definir um identificador canônico com migração e regressão multi-tenant antes de remover as variantes.
- **Prioridade:** P2 de modelo de dados preexistente; mudança funcional fora deste GOAL.

## 23. Espelhar pendências em um rastreador oficial
- **Fonte:** Code Review Dominus-MCP do commit `ed9929d5052d4f04273a764e5755847a0f88fc9d`.
- **Arquivo:** `CODE_REVIEW_HUMAN_BACKLOG.md`.
- **Evidência:** pendências mantidas apenas em Markdown podem perder visibilidade de planejamento conforme o repositório evolui.
- **Ação sugerida:** converter os itens priorizados em issues/cards no rastreador adotado pela equipe e manter links bidirecionais.
- **Prioridade:** P3 de processo; não bloqueante.

## 24. Reutilizar o resolvedor de imports relativos na guarda do módulo legado
- **Fonte:** Code Review Dominus-MCP do commit `e81c141d71affe0a8267742cd43f900616ca30c7`.
- **Arquivo:** `project-hub/backend/tests/test_legacy_cleanup.py` (`test_removed_compatibility_layers_and_helpers_stay_absent`).
- **Evidência:** a verificação de imports de `identity_service` ainda possui lógica própria e não reconhece todas as formas relativas, embora o teste também confirme que o arquivo físico foi removido e um import residual falharia em runtime.
- **Ação sugerida:** generalizar `_resolved_import_from_module` para um detector reutilizável de módulos e aplicar a mesma varredura aos dois guardrails em uma limpeza futura dos testes.
- **Prioridade:** P3 de consistência de teste; sem regressão funcional e não bloqueante.
