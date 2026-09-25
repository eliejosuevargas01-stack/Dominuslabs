# IMPLEMENTATION PLAN — Dominus Product & Architecture Refoundation

> **Status:** CANONICAL — Master Implementation Plan  
> **Source of truth:** `GOAL.md` + `CONTRACTS.md`  
> **Rule:** este documento define ordem e dependências; `TASKS.md` registra execução.

## Objetivo

Refatorar progressivamente o Dominus para uma plataforma operacional confiável, mobile-first e pronta para produção sem enfraquecer Zero Trust, isolamento multi-tenant ou contratos M2M.

A implementação não é um redesign isolado. Os problemas de UX, dados, eventos, mídia, realtime e arquitetura estão conectados e devem ser resolvidos na ordem de dependência.

## Fluxo macro

```text
BASELINE
→ FAIL-CLOSED
→ DATA INTEGRITY
→ EVENT CONTRACT
→ MEDIA OWNERSHIP
→ PAGINATION
→ GLOBAL REALTIME
→ NOTIFICATIONS
→ OMNICHANNEL
→ ERROR UX
→ APP SHELL
→ MOBILE
→ PRODUCT AREAS
→ BACKEND/WA DECOMPOSITION
→ PERFORMANCE
→ PWA
→ TESTS
→ ACCESSIBILITY
→ OBSERVABILITY
→ LEGACY CLEANUP
→ DOCUMENTATION
```

## Regras de execução

### R1 — Sem fallback implícito que altere semântica

Proibido:

```text
valorReal || valorInventado
sessaoConectada || primeiraSessao
dadosHoje.length ? dadosHoje : historicoCompleto
```

Defaults apenas visuais ou de formatação podem existir quando não mudam regra de negócio, segurança ou integridade.

### R2 — Fail-closed

Configuração crítica ausente deve impedir startup. Não abrir porta para falhar apenas na primeira requisição.

### R3 — Dados reais

Zero é válido. Null é válido quando semanticamente correto. Indisponível é válido. Dado demonstrativo em produção não é válido.

### R4 — Sem catch vazio em operação relevante

Erros de dados, sessão, mensagens, pagamentos, mídia, auth, realtime, pedidos e integrações devem ser observáveis.

### R5 — Não trocar um monólito por outro

Decompor por responsabilidade de domínio.

### R6 — Preservar Zero Trust

Nenhuma mudança pode remover tenant validation, session ownership, JWKS validation, scopes, isolamento multi-tenant ou expor M2M ao browser.

### R7 — Destrutivo exige prova

Antes de remover endpoint, rota, handler, serviço, componente ou workflow, localizar consumidores e comprovar substituição.

---

# FASE 0 — INVENTÁRIO E BASELINE

## ARCH-000 — Congelar estado atual

Registrar commits, workflows, env names, endpoints, eventos, testes, screenshots e bugs reproduzidos.

**Gate:** baseline documentado antes das mudanças estruturais.

---

# FASE 1 — FALLBACKS E FAIL-CLOSED

## ARCH-001 — Inventário de fallbacks

Classificar ocorrências em:

```text
SAFE_UI_DEFAULT
SAFE_FORMATTING_DEFAULT
RETRY
DANGEROUS_FALLBACK
SECURITY_FALLBACK
DATA_INTEGRITY_FALLBACK
SESSION_FALLBACK
CONFIG_FALLBACK
LEGACY_COMPATIBILITY
```

## ARCH-002 — Configuração obrigatória

Schemas de environment por serviço e startup fail-closed.

## ARCH-003 — Remover defaults sensíveis

Nenhum secret, credential, tenant ou endpoint operacional real como fallback funcional.

## ARCH-004 — Auditoria de .env

Retirar secrets versionados, rotacionar valores afetados e manter apenas exemplos neutros.

**Gate da fase:** nenhum secret crítico possui fallback funcional.

---

# FASE 2 — INTEGRIDADE DE DADOS

## DATA-001 — Pedidos Hoje

Hoje sem pedidos = 0. Nunca usar histórico como substituto.

## DATA-002 — Remover métricas inventadas

Sem dado = 0, null ou indisponível conforme semântica.

## DATA-003 — Períodos reais

Hoje/7d/30d alteram a query real no timezone do tenant.

## DATA-004 — Lista coerente com período

Tabela/lista deve refletir o filtro ou declarar claramente independência.

**Gate:** nenhum dashboard apresenta dado demonstrativo como real.

---

# FASE 3 — CONTRATO ÚNICO DE EVENTOS

## EVT-001 — Catálogo atual

Mapear WA API, n8n, Dominus, SSE e duplicações semânticas.

## EVT-002 — SystemEvent

Contrato base:

```json
{
  "version": 1,
  "event_id": "uuid",
  "type": "message.created",
  "tenant_id": "tenant",
  "session_id": "session",
  "occurred_at": "ISO-8601",
  "payload": {}
}
```

## EVT-003 — Tipos canônicos

```text
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
```

## EVT-004 — Event Ingress

Endpoint do Dominus:

```http
POST /api/v1/webhooks/events
```

Responsabilidades: assinatura, timestamp, event ID, idempotência, tenant, schema, logging e routing.

## EVT-005 — Event Router

HTTP fino; handlers separados por tipo.

## EVT-006 — Semântica de status

`message.status.updated` nunca cria mensagem, incrementa unread, toca som ou gera browser notification.

## EVT-007 — n8n como router

n8n roteia por `type`; não inventa um novo tipo semântico.

## EVT-008 — Deprecação segura

Migrar consumidores antes de remover endpoints legados.

**Gate:** a semântica do evento permanece estável ponta a ponta.

---

# FASE 4 — MEDIA OWNERSHIP

## MEDIA-001 — Consolidar domínio de mídia na Whats API

Extrair lifecycle e responsabilidades do monólito sem regressão.

## MEDIA-002 — State machine

```text
pending → downloading → ready | failed
```

Mensagem é persistida mesmo se mídia falhar.

## MEDIA-003 — Storage tenant-aware

```text
/app/data/media/{tenant}/{session}/...
```

Validar MIME, tamanho, nome seguro e path.

## MEDIA-004 — GET serve persistido

`GET media` não baixa silenciosamente do WhatsApp como fallback. Processing/failed/missing devem retornar estados/erros tipados.

## MEDIA-005 — Retry explícito

Retry limitado, observável e separado do GET.

## MEDIA-006 — Eventos de mídia

Emitir `media.processing`, `media.ready` e `media.failed` quando aplicável.

**Gate:** frontend não depende operacionalmente de URLs temporárias do WhatsApp.

---

# FASE 5 — PAGINAÇÃO

## PAG-001 — Conversas

Cursor pagination, aproximadamente 30 iniciais, IntersectionObserver e realtime sem reset total.

## PAG-002 — Mensagens

Aproximadamente 50 últimas ao abrir; scroll up carrega anteriores com cursor `before`, prepend e preservação do scroll anchor.

## PAG-003 — Deduplicação

Chave por tenant/session/message_id; realtime e paginação não duplicam elementos.

---

# FASE 6 — REALTIME GLOBAL

## RT-001 — RealtimeProvider

Mover realtime para a aplicação autenticada, fora do lifecycle do Omnichannel.

## RT-002 — Event router frontend

Centralizar dispatch por tipo, dedupe e reconexão.

## RT-003 — Pedidos e WhatsApp

Mesma infraestrutura global pode receber domínios distintos sem acoplá-los a páginas.

**Gate:** sair do Omnichannel não interrompe eventos de mensagens.

---

# FASE 7 — NOTIFICAÇÕES

## NOTIF-001 — Sound Engine

Som principal somente para:

```text
message.created AND incoming AND não processado
```

## NOTIF-002 — Browser Notification API

Notificação quando a aplicação está aberta, porém em background, com deep link para conversa.

## NOTIF-003 — Regras negativas

Nunca notificar como nova mensagem: status/read/delivered/played/reaction/outgoing/conversation.updated/media.ready.

---

# FASE 8 — OMNICHANNEL

## OMN-001 — Decomposição

Separar ConversationList, Chat, MessageBubble, composer, session selector e data hooks.

## OMN-002 — Seleção de sessão

Persistir última sessão apenas se ainda estiver WORKING. Nenhum fallback para sessão desconectada/primeiro item.

## OMN-003 — Avatares

Authenticated fetch + lazy loading + cache tenant/session/JID.

## OMN-004 — Media renderers

Renderers específicos para image, video, audio, document e sticker.

## OMN-005 — MediaViewer

Imagem com zoom/pan; vídeo fullscreen; sticker pequeno/transparente.

## OMN-006 — Estados

Loading, empty, partial, error, disconnected e permission explícitos.

---

# FASE 9 — ERROR UX

## ERR-001 — AppError

Contrato frontend normalizado baseado em código, mensagem, retryable, suggested_action e correlation_id quando disponível.

## ERR-002 — Presentation rules

Toast para transient; inline para área local; banner para problema sistêmico; blocking state quando operação é impossível.

## ERR-003 — Remover erros silenciosos

Eliminar catches vazios em fluxos relevantes.

---

# FASE 10 — APP SHELL E NAVEGAÇÃO

## SHELL-001 — Navegação tenant

```text
Início
Atendimento
Pedidos
Clientes
Campanhas
Automações
Cardápio
Canais
Integrações
Funcionário Digital
Minha Empresa
Mais soluções
```

Project Hub é interno/admin.

## SHELL-002 — Linguagem

Remover linguagem corporativa artificial e nomes de infraestrutura da UX.

---

# FASE 11 — MOBILE-FIRST

## MOBILE-001 — Mobile shell

Bottom navigation: Início, Atendimento, Pedidos, Clientes, Mais.

## MOBILE-002 — Omnichannel mobile

Lista e chat são telas distintas; `100dvh`, safe areas, composer sticky e touch targets adequados.

## MOBILE-003 — Overflow

Zero page-level horizontal overflow e zero sobreposição de drawer/header/composer.

---

# FASE 12 — MINHA EMPRESA

## EMP-001 — Reestruturar Company Settings

Seções: Dados da loja, Atendimento, Entrega, Pagamentos, Cardápio, Promoções e Políticas.

## EMP-002 — Navegação de seções

Desktop: ScrollableTabs com setas/fade/scrollIntoView. Mobile: select, menu ou bottom sheet; sem tabs comprimidas.

---

# FASE 13 — FUNCIONÁRIO DIGITAL

## FD-001 — Conceito de produto

Substituir “IA” como conceito principal por “Funcionário Digital”.

## FD-002 — Trabalho real

Mostrar atendimentos, pedidos, clientes recuperados e vendas assistidas.

## FD-003 — Configuração

Tom, ações permitidas, escalonamento, limites, políticas e horário.

Detalhes de modelo/provider/tokens ficam em área avançada.

---

# FASE 14 — ORDER MANAGER

## OM-001 — Operação primeiro

Board principal:

```text
NOVOS
PREPARANDO
PRONTOS
EM ENTREGA
```

## OM-002 — Cards compactos

Idade, cliente, itens, valor, pagamento, entrega, endereço, origem e ação principal.

## OM-003 — Métricas operacionais

Novos, atrasados, preparando, receita do dia e tempo médio.

---

# FASE 15 — DASHBOARD / INÍCIO

## DASH-001 — Métricas reais

Reusar contratos corrigidos da Fase 2.

## DASH-002 — Visão operacional

Priorizar o que precisa de atenção agora; evitar showcase de métricas sem ação.

---

# FASE 16 — MEU PERFIL

## PERF-001 — Perfil separado do tenant

Nome, email, foto, senha, sessões de autenticação e preferências suportadas.

## PERF-002 — Preferências

Notificações, som, tema e idioma somente quando realmente suportados.

---

# FASE 17 — BACKEND DOMINUS

## DEC-BE-001 — webhooks.py

Endpoints finos e roteamento por domínio.

## DEC-BE-002 — n8n_service.py

Separar persistência, queries, integração externa e regras.

## DEC-BE-003 — Correlation IDs

Propagar request/event correlation sem transformá-lo em autoridade.

---

# FASE 18 — WHATS API

## DEC-WA-001 — session.manager.js

Decompor por session, messages, media, contacts, sending e events.

## DEC-WA-002 — Limpeza legacy

Remover caminhos antigos somente após consumer proof e testes.

---

# FASE 19 — DESIGN SYSTEM / FRONTEND SKILL

## SKILL-001 — dominus-frontend

Documentar tokens, spacing, typography, breakpoints, shells, tabelas, dialogs, media viewer, estados, acessibilidade e padrões proibidos.

---

# FASE 20 — PERFORMANCE

## PERF-OPT-001 — Conversas/mensagens

Medir payloads e renderização; virtualização apenas se dados mostrarem necessidade.

## PERF-OPT-002 — Avatares e mídia

Cache, lazy loading e cancelamento de requisições obsoletas.

---

# FASE 21 — PWA / APP EXPERIENCE

## PWA-001 — Manifest/installability

Somente após shell/realtime/notificações estabilizados.

## PWA-002 — Service Worker + Web Push

Etapa separada da Notification API. Não tratar como requisito para realtime global inicial.

---

# FASE 22 — TESTES UNITÁRIOS E DE CONTRATO

## TEST-001 — Events

Schema, routing, idempotência e semântica.

## TEST-002 — Media

State machine, tenant paths, ready/failed/missing e retry.

## TEST-003 — Pagination

Cursor, ordering, dedupe e scroll anchor.

## TEST-004 — Notification rules

Som/browser notifications apenas nos eventos permitidos.

---

# FASE 23 — E2E / REGRESSÃO

## E2E-001 — Playwright

Breakpoints:

```text
375x812
390x844
414x896
768x1024
1366x768
1440x900
1920x1080
```

Validar overflow=0, controles sem sobreposição, dados fake=0 e fluxo crítico ponta a ponta.

---

# FASE 24 — ACESSIBILIDADE

## A11Y-001

Keyboard navigation, focus visível, labels, contraste e touch targets.

---

# FASE 25 — OBSERVABILIDADE

## OBS-001

Correlation IDs, event IDs, media lifecycle, logs estruturados e erros sanitizados.

## OBS-002

Não registrar tokens, keys, payloads sensíveis ou credenciais.

---

# FASE 26 — LEGACY CLEANUP

## LEGACY-001

Reauditar endpoints, wrappers, aliases, docs e compatibilidade temporária.

## LEGACY-002

Remover somente após consumer proof.

---

# FASE 27 — DOCUMENTAÇÃO FINAL

## DOC-001

Sincronizar README, architecture, integration guides, service READMEs, PLAN, TASKS e runbooks.

## DOC-002

Arquivar artefatos históricos e remover topologia operacional desnecessária de repositórios públicos.

---

# Cenário sistêmico de validação

O Refoundation só é considerado completo quando o cenário abaixo funciona:

1. login de usuário;
2. Dashboard mostra 0 se não houver pedidos hoje;
3. sessão desconectada anterior não é escolhida silenciosamente;
4. sidebar carrega primeiro lote e avatares sob demanda;
5. chat abre últimas mensagens e carrega antigas sem salto;
6. `message.created` incoming toca som uma única vez;
7. `message.status.updated` atualiza checks sem som/notificação;
8. imagem/vídeo/sticker usam renderização adequada;
9. mídia persistida funciona sem URL original do WhatsApp;
10. navegação para Pedidos não interrompe realtime de mensagens;
11. Minha Empresa não cria overflow horizontal;
12. mobile usa shell próprio e chat ocupa viewport útil;
13. erros relevantes são visíveis e acionáveis;
14. Zero Trust e isolamento multi-tenant permanecem intactos.

# Definition of Done global

- segurança e tenant isolation preservados;
- dados reais;
- eventos semanticamente estáveis;
- media ownership na Whats API;
- paginação por cursor;
- realtime global;
- notificações determinísticas;
- Omnichannel decomposto;
- mobile próprio;
- documentação sem duas arquiteturas concorrentes;
- testes cobrindo contratos críticos.
