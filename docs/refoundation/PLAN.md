# IMPLEMENTATION PLAN — Dominus Product & Architecture Refoundation

## Status

Planejamento de refatoração sistêmica.

## Repositórios envolvidos

- `Dominuslabs`
- `IDC_Dominuslabs`
- `api_whatsapp_v1.2`
- workflows n8n envolvidos no fluxo WhatsApp → Dominus

## Objetivo

Executar uma refatoração progressiva da arquitetura e da experiência do Dominus para transformá-lo em uma plataforma operacional confiável, moderna, mobile-first e pronta para produção.

A implementação não deve ser tratada como redesign isolado.

Existem problemas relacionados entre si em:

- configuração;
- segurança;
- fallbacks;
- contratos entre serviços;
- processamento de eventos;
- mídia;
- mensagens;
- realtime;
- notificações;
- paginação;
- arquitetura frontend;
- arquitetura backend;
- arquitetura Whats API;
- UX de erro;
- mobile;
- métricas;
- nomenclatura;
- organização do produto.

A ordem de implementação deve respeitar dependências.

Fluxo macro:

~~~text
AUDITORIA
  ↓
FAIL-CLOSED
  ↓
CONTRATOS
  ↓
EVENTOS
  ↓
MÍDIA
  ↓
PAGINAÇÃO
  ↓
REALTIME GLOBAL
  ↓
OMNICHANNEL
  ↓
ERROR UX
  ↓
APP SHELL
  ↓
MOBILE
  ↓
ORDER MANAGER
  ↓
DASHBOARD
  ↓
MINHA EMPRESA
  ↓
FUNCIONÁRIO DIGITAL
  ↓
PERFIL
  ↓
DECOMPOSIÇÃO FINAL
  ↓
E2E / REGRESSÃO
~~~

---

# REGRAS DE EXECUÇÃO

## R1 — Nenhum fallback implícito novo

Não introduzir comportamento do tipo:

~~~ts
valorReal || valorInventado
sessaoConectada || primeiraSessao
dadosHoje.length ? dadosHoje : historicoCompleto
~~~

quando o segundo valor altera a semântica da operação.

---

## R2 — Não corrigir erro de arquitetura escondendo estado

Exemplo proibido:

~~~text
sessão desconectada
→ selecionar outra silenciosamente
~~~

Correto:

~~~text
sessão desconectada
→ mostrar estado
→ impedir operação incorreta
→ permitir ação consciente do usuário
~~~

---

## R3 — Não inventar dados

Nenhum dado de produção pode utilizar valor demonstrativo ou hardcoded para preencher interface.

Zero é válido.

Null é válido quando semanticamente adequado.

Indisponível é válido.

Erro visível é válido.

Dado falso não é válido.

---

## R4 — Não usar catch vazio em operação relevante

Proibido:

~~~ts
.catch(() => {})
~~~

quando a operação afeta:

- dados;
- sessão;
- mensagens;
- pagamentos;
- mídia;
- autenticação;
- realtime;
- preferências;
- pedidos;
- perfil;
- integrações.

---

## R5 — Não transformar refatoração em novos monólitos

Não retirar 2.700 linhas de um arquivo apenas para criar outro arquivo de 2.000 linhas.

Dividir por responsabilidade de domínio.

---

## R6 — Preservar Zero Trust

Nenhuma simplificação de frontend ou API pode:

- remover tenant validation;
- confiar em tenant enviado pelo browser;
- remover ownership de sessão;
- expor M2M JWT ao frontend;
- expor keys;
- remover JWKS validation;
- relaxar scopes;
- introduzir endpoints públicos de mídia sem autorização apropriada.

---

## R7 — Mudanças destrutivas exigem prova de substituição

Antes de deletar:

- endpoint;
- função;
- rota;
- handler;
- componente;
- serviço;
- workflow;

localizar todos os consumidores.

Somente remover quando comprovadamente substituído.

---

# FASE 0 — INVENTÁRIO E BASELINE

## ARCH-000 — Congelar estado atual

Antes de alterações estruturais:

1. registrar commit SHA dos três repositórios;
2. listar workflows n8n envolvidos;
3. registrar variáveis de ambiente necessárias sem expor valores;
4. registrar endpoints atualmente utilizados;
5. registrar eventos emitidos;
6. registrar eventos consumidos;
7. executar suites existentes;
8. guardar baseline de screenshots desktop/mobile;
9. registrar problemas já reproduzidos.

Problemas obrigatórios no baseline:

~~~text
- "Pedidos Hoje" exibe histórico quando hoje está vazio.
- métricas de IA usam valores hardcoded.
- sessão inicial pode ser desconectada.
- imagens não possuem experiência adequada de expansão.
- vídeos não possuem viewer/fullscreen adequado.
- stickers caem no renderer genérico de imagem.
- avatars da sidebar não seguem o mesmo pipeline do chat.
- notificações do WhatsApp só funcionam com Omnichannel montado.
- status update pode resultar em som de nova mensagem.
- browser notifications não existem.
- mobile utiliza sidebar/drawer desktop adaptado.
- drawer possui problema de sobreposição próximo ao logo.
- Omnichannel mobile perde área útil com múltiplos headers.
- Company Settings possui overflow horizontal ruim.
- Project Hub aparece para tenants.
- não existe Meu Perfil.
~~~

### Aceite

Baseline documentado antes da primeira alteração.

---

# FASE 1 — AUDITORIA DE FALLBACKS E FAIL-CLOSED

## ARCH-001 — Inventário de fallbacks

Auditar:

~~~text
Dominuslabs
IDC_Dominuslabs
api_whatsapp_v1.2
~~~

Buscar padrões:

~~~text
||
??
ternários de fallback
DEFAULT_
default=
os.getenv(..., "valor")
process.env.X || "valor"
catch vazio
except: pass
mock value
fake metric
primeiro item de array como fallback
"default" session
hardcoded tenant
hardcoded credential
hardcoded endpoint
~~~

Não tratar todos os `||` como erro.

Classificar cada ocorrência:

~~~text
SAFE_UI_DEFAULT
SAFE_FORMATTING_DEFAULT
RETRY
DANGEROUS_FALLBACK
SECURITY_FALLBACK
DATA_INTEGRITY_FALLBACK
SESSION_FALLBACK
CONFIG_FALLBACK
LEGACY_COMPATIBILITY
~~~

Criar relatório antes da remoção.

---

## ARCH-002 — Configuração obrigatória

Criar schemas de environment por aplicação.

### Dominus

Auditar obrigatoriedade de:

~~~text
DATABASE_URL
JWT_SECRET
IDENTITY_WORKER_URL
IDPW / M2M client identity
DOMINUS_PRIVATE_KEY
IDPW_PUBLIC_KEY ou JWKS config
WHATSAPP_API_URL
WHATS_API_PUBLIC_KEY
N8N_WEBHOOK_SECRET
ENCRYPTION_MASTER_KEY
CORS config
~~~

### Whats API

Auditar:

~~~text
DATABASE_URL
JWT_ISSUER
JWT_AUDIENCE
IDPW_JWKS_URL
WHATS_API_PRIVATE_KEY
DOMINUS_PUBLIC_KEY
DATA_DIR
MEDIA_DIR
SESSIONS_DIR
WEBHOOK_URL / webhook configuration
WEBHOOK_SECRET
~~~

### IDC

Auditar:

~~~text
JWT_ISSUER
signing private key
public key/JWKS metadata
allowed clients
allowed audiences
allowed scopes
policy storage
anti-replay storage
~~~

### Comportamento obrigatório

Se configuração crítica estiver ausente:

~~~text
startup
→ validação
→ erro estruturado
→ exit code != 0
→ NÃO iniciar servidor
~~~

Não abrir porta para depois falhar na primeira requisição.

---

## ARCH-003 — Remover defaults sensíveis

Eliminar defaults conhecidos como:

~~~text
admin123
secret-production
encryption key previsível
JWT key previsível
webhook secret previsível
tenant admin default
URLs reais da infraestrutura
~~~

de:

- Docker Compose;
- source code;
- config modules;
- exemplos públicos.

`.env.example`:

~~~env
JWT_ISSUER=
JWT_AUDIENCE=
IDPW_URL=
IDPW_JWKS_URL=
DATABASE_URL=
MEDIA_DIR=/app/data/media
~~~

A presença de `/app/data/media` como caminho estrutural não é segredo.

Hostname real da infraestrutura não deve ser colocado como default.

---

## ARCH-004 — Auditoria do `.env` versionado

Verificar se `.env` existente no Git contém ou já conteve credenciais.

Ações:

1. identificar secrets presentes;
2. rotacionar secrets reais afetados;
3. retirar `.env` do tracking;
4. manter apenas `.env.example`;
5. avaliar limpeza do histórico conforme necessidade;
6. verificar logs/build artifacts que possam conter valores.

### Aceite da Fase 1

- nenhum secret crítico possui fallback funcional;
- startup falha sem config necessária;
- nenhum dado real de infraestrutura desnecessário permanece como default público;
- inventário de fallbacks produzido;
- valores demonstrativos de produção identificados.

---

# FASE 2 — CORREÇÃO DA INTEGRIDADE DOS DADOS

## DATA-001 — Corrigir "Pedidos Hoje"

Problema atual:

~~~ts
const activeSet = todayList.length > 0
  ? todayList
  : rawList;
~~~

Esse comportamento deve ser eliminado.

Correto:

~~~text
Hoje sem pedidos
→ Pedidos Hoje = 0
→ Faturamento Hoje = R$ 0,00
~~~

Não utilizar histórico.

---

## DATA-002 — Remover métricas inventadas

Remover comportamentos equivalentes a:

~~~ts
atendimentosIa: iaCount || 14
atendimentosHumanos: humanCount || 2
porcentagemIa: pctIa > 0 ? pctIa : 88
~~~

Sem dado:

~~~text
—
Dados ainda não disponíveis
~~~

ou `0`, conforme semântica.

---

## DATA-003 — Período real de métricas

Hoje / 7 dias / 30 dias deve alterar dados reais.

Criar backend analítico.

Sugestão:

~~~http
GET /analytics/overview?period=today
GET /analytics/overview?period=7d
GET /analytics/overview?period=30d
~~~

Ou:

~~~http
GET /analytics/overview?from=...&to=...
~~~

O backend deve controlar timezone.

Não calcular "hoje" usando timezone arbitrário do browser se o tenant possuir timezone configurado.

Resposta exemplo:

~~~json
{
  "period": {
    "from": "...",
    "to": "...",
    "timezone": "America/Sao_Paulo"
  },
  "orders": 0,
  "revenue": 0,
  "average_ticket": null,
  "conversion_rate": null
}
~~~

---

## DATA-004 — Pedidos recentes respeitam filtro

A lista "Pedidos recentes" deverá refletir o período selecionado ou deixar claro que é independente dele.

Não misturar:

~~~text
cards = hoje
tabela = histórico completo
~~~

sem informar.

### Aceite

Se hoje não tiver nenhum pedido, a tela deverá mostrar 0, independentemente da existência de pedidos históricos.

---

# FASE 3 — CONTRATO ÚNICO DE EVENTOS

## EVT-001 — Catalogar eventos atuais

Mapear:

### Whats API

~~~text
message.created
message.updated
session events
webhook events
media lifecycle
~~~

### n8n

Mapear Switch/IFs que roteiam cada payload.

### Dominus

Mapear:

~~~text
/crm/update-chat
/crm/message-status
/webhooks/inbound/whatsapp
SSE crm-chats
outros endpoints equivalentes
~~~

Identificar duplicações semânticas.

---

## EVT-002 — Schema SystemEvent

Criar contrato versionado:

~~~json
{
  "version": 1,
  "event_id": "uuid",
  "type": "message.created",
  "tenant_id": "tenant",
  "session_id": "session",
  "occurred_at": "2026-09-23T20:00:00Z",
  "payload": {}
}
~~~

Campos obrigatórios devem depender do evento quando necessário.

---

## EVT-003 — Tipos canônicos

Inicialmente:

~~~text
message.created
message.status.updated
message.reaction.updated

conversation.updated

media.processing
media.ready
media.failed

session.connected
session.disconnected
session.qr.updated

order.created
order.updated
order.cancelled
~~~

Evitar nomes vagos:

~~~text
update-chat
update
sync
data
event
~~~

---

## EVT-004 — Event Ingress único

Criar no Dominus:

~~~http
POST /webhooks/events
~~~

Esse endpoint é o ponto de entrada de eventos assíncronos.

Responsabilidades:

~~~text
signature validation
timestamp validation
event ID
idempotency
tenant
schema
routing
logging
~~~

Ele NÃO deve implementar lógica de todos os tipos dentro do endpoint.

Fluxo:

~~~text
HTTP
 ↓
EventIngress
 ↓
EventValidator
 ↓
EventRouter
 ↓
handler específico
~~~

---

## EVT-005 — Event Router

Estrutura sugerida:

~~~text
project-hub/backend/app/events/
├── schemas.py
├── registry.py
├── router.py
├── errors.py
└── handlers/
    ├── message_created.py
    ├── message_status_updated.py
    ├── message_reaction_updated.py
    ├── media_ready.py
    ├── media_failed.py
    ├── session_connected.py
    ├── session_disconnected.py
    └── order_events.py
~~~

---

## EVT-006 — Regra fundamental de mensagem

`message.status.updated`:

~~~text
pode:
- atualizar status
- atualizar checks
- atualizar timestamp se necessário

não pode:
- incrementar unread
- criar nova mensagem
- tocar som
- emitir browser notification
- mover conversa por "nova mensagem" sem motivo
~~~

---

## EVT-007 — n8n como router, não tradutor semântico

O Switch n8n deve usar `type`.

Exemplo:

~~~text
type
├── message.created
├── message.status.updated
├── media.ready
├── session.connected
└── ...
~~~

Não reconstruir arbitrariamente o tipo.

---

## EVT-008 — Deprecar endpoints antigos

Após migração completa:

- descobrir consumidores;
- migrá-los;
- criar logs temporários para detectar chamadas restantes;
- remover endpoints sem consumidor.

Não manter endpoints "por garantia" indefinidamente.

### Aceite

Uma leitura de mensagem no celular deve produzir:

~~~text
message.status.updated