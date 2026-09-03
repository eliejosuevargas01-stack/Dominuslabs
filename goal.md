# 🎯 Macro Goal: Estabilização de Mídias/Avatares no Omnichannel e Alarme Global

## Objetivo Principal
Corrigir no frontend Dominuslabs:
1. **Ponto 2 - Áudios, Mídias e Avatares no Omnichannel (`OmnichannelView.tsx`):**
   - Eliminar URLs relativas que batem no servidor estático do Render (`/api/whatsapp/...`), redirecionando-as para o backend oficial (`API_BASE` / `https://dominuslabs.online`).
   - Garantir a inclusão do prefixo correto (`/api/v1/whatsapp/sessions/{session_id}/media` e `/avatar`).
   - Anexar o parâmetro obrigatório de autenticação `token=${token}` nas URLs de mídia e avatar para atender ao contrato de segurança do backend sem causar 401 ou CORB.
2. **Alarme Global (`GlobalOrderNotification.tsx`):**
   - Eliminar fallbacks hardcoded para `localhost:8000`.
   - Utilizar a resolução dinâmica de URL (`getDynamicApiUrl()` / `API_BASE`) para chamadas REST e converter a URL HTTP para WebSocket dinamicamente (`ws://` ou `wss://` conforme o protocolo da página ou host do backend), acabando com o spam de CORS no console de produção.

## Critérios de Aceitação
- Áudios e mídias no chat do WhatsApp tocam e carregam com status 200 diretamente do backend.
- Avatares de contatos carregam sem erro de CORB (`net::ERR_BLOCKED_BY_ORB`) e com fallback resiliente.
- Componente `GlobalOrderNotification` conecta na URL de API e WebSocket correspondente ao ambiente de execução, sem tentar `localhost:8000` em produção.
- Todos os testes unitários do Vitest executam e passam com 100% de sucesso.
