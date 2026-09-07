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
