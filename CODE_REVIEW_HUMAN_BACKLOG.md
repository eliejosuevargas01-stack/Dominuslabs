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
