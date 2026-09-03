# Code Review Human Backlog

Itens e melhorias não-bloqueantes apontados pelo Code Review (Dominus-MCP) para acompanhamento técnico futuro:

## 1. Tipagem Estrita TypeScript e Redução de `any`
- **Arquivos:** `src/components/GlobalOrderNotification.tsx`, `src/pages/OmnichannelView.tsx`
- **Evidência:** Uso de `any` em estados de listas como conversas e contatos (`useState<any[]>`), em referências de timer (`recordingTimerRef = useRef<any>(null)`), e coerção de tipo como `(oscillatorRef.current as any)._pulseInterval`.
- **Ação Sugerida:** Declarar interfaces formais explícitas (`IContact`, `IMessage`, `IOmniSession`) e criar refs dedicadas para timers e osciladores em substituição à tipagem flexível.
- **Prioridade:** P2 (Não bloqueante para deploy).
