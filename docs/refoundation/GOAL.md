# GOAL — Dominus Product & Architecture Refoundation

## Missão

Transformar o Dominus de um painel administrativo funcional, porém fragmentado, inconsistente e ainda com características de protótipo, em uma plataforma operacional moderna, confiável, mobile-first e pronta para produção.

O Dominus deve voltar ao conceito original do produto:

> Um funcionário digital e sistema operacional para pequenos e médios negócios que atende clientes, vende, recebe pedidos, cobra, acompanha entregas, fideliza clientes, executa campanhas e fornece inteligência comercial — sem obrigar o usuário a entender IA, APIs, webhooks, infraestrutura ou terminologia corporativa artificial.

A missão abrange em conjunto:

- `Dominuslabs`
- `IDC_Dominuslabs`
- `api_whatsapp_v1.2`
- fluxos n8n relacionados à integração WhatsApp → Dominus

Nenhuma melhoria de UX poderá enfraquecer Zero Trust, isolamento multi-tenant, autenticação M2M, ownership de sessões ou segurança criptográfica.

---

# 1. PRINCÍPIOS NÃO NEGOCIÁVEIS

## 1.1 No implicit fallback

O sistema não deve mascarar:

- configuração ausente;
- secret ausente;
- sessão desconectada;
- dado inexistente;
- falha de serviço;
- métrica não calculável;
- estado inválido;
- falha de mídia;
- falha de autenticação;
- falha de ownership.

É proibido utilizar fallback silencioso para fazer o sistema "continuar funcionando" quando o requisito real não foi cumprido.

Exemplos proibidos:

~~~ts
workingSession || availableSessions[0]

todayOrders.length > 0
  ? todayOrders
  : historicalOrders

iaCount || 14

percentage > 0
  ? percentage
  : 88
~~~

Exemplos proibidos em configuração:

~~~env
JWT_SECRET=${JWT_SECRET:-secret-default}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
~~~

O comportamento correto é:

~~~text
requisito válido
→ operação

requisito inválido/ausente
→ fail closed
→ erro observável
→ mensagem útil
→ ação recomendada quando possível
~~~

Retries explícitos, limitados e observáveis da mesma operação não são considerados fallback.

---

# 2. CONFIGURAÇÃO E SEGURANÇA

Todos os valores críticos devem ser fornecidos exclusivamente pelo ambiente de execução.

O código não deve possuir valores reais nem defaults funcionais para:

- JWT issuer;
- JWT audience;
- IDPW URL;
- JWKS URL;
- secrets;
- private keys;
- encryption keys;
- webhook secrets;
- URLs internas;
- credentials;
- tenant IDs;
- admin credentials.

Produção deve recusar startup caso uma configuração obrigatória esteja ausente ou inválida.

O `.env.example` deve documentar somente nomes e formatos neutros:

~~~env
JWT_ISSUER=
JWT_AUDIENCE=
IDPW_URL=
IDPW_JWKS_URL=
~~~

Nunca expor infraestrutura real desnecessariamente em defaults públicos.

---

# 3. EVENTOS DO SISTEMA

Eventos assíncronos devem utilizar contrato único e tipado.

Eliminar rotas redundantes e semanticamente sobrepostas como mecanismos diferentes para:

- nova mensagem;
- atualização de mensagem;
- atualização de chat;
- status de mensagem;
- reação;
- atualização de sessão.

Criar um único Event Ingress para eventos assíncronos.

Contrato base:

~~~json
{
  "event_id": "unique-id",
  "type": "message.created",
  "tenant_id": "tenant-id",
  "session_id": "session-id",
  "occurred_at": "ISO-8601",
  "payload": {}
}
~~~

Tipos iniciais:

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
order.created
order.updated
~~~

Um evento nunca pode mudar de semântica durante o pipeline.

Exemplo obrigatório:

~~~text
message.status.updated
~~~

jamais poderá virar:

~~~text
message.created
~~~

---

# 4. WHATSAPP MEDIA OWNERSHIP

A Whats API será proprietária do lifecycle das mídias recebidas do WhatsApp.

A aplicação não deve depender permanentemente de URLs temporárias fornecidas pelos servidores do WhatsApp.

Fluxo esperado:

~~~text
WhatsApp
→ metadata da mensagem
→ downloadMediaMessage()
→ arquivo local persistente
→ metadata persistida
→ URL interna controlada pela Whats API
→ Dominus
→ frontend
~~~

O frontend nunca deverá depender operacionalmente de:

~~~text
pps.whatsapp.net
fbcdn.net
directPath
URLs temporárias do WhatsApp
~~~

O arquivo deverá ser armazenado no volume persistente da Whats API.

Exemplo:

~~~text
/app/data/media/{tenant}/{session}/...
~~~

A mídia deve possuir state machine explícita:

~~~text
pending
downloading
ready
failed
~~~

Falha de download não deve apagar ou invalidar a mensagem.

Não utilizar URL do WhatsApp como fallback.

---

# 5. PAGINAÇÃO OBRIGATÓRIA

Conversas e mensagens não devem ser carregadas completamente.

## Conversas

Carregar inicialmente as conversas mais recentes.

Exemplo:

~~~text
30 conversas
~~~

Quando o usuário chegar próximo ao final da lista:

~~~text
IntersectionObserver
→ próxima página
→ append
~~~

Usar cursor pagination.

## Mensagens

Ao abrir uma conversa:

~~~text
últimas 50 mensagens
~~~

Ao subir em direção ao histórico:

~~~text
carregar mensagens anteriores
→ prepend
→ manter scroll anchor
~~~

Nunca carregar todo o histórico de uma conversa inicialmente.

---

# 6. OMNICHANNEL

O Omnichannel deverá ser reestruturado para funcionar como um aplicativo de mensagens profissional.

Problemas atuais a eliminar:

- `OmnichannelView.tsx` monolítico;
- mídia parcialmente suportada;
- imagens sem experiência adequada de expansão;
- vídeos presos ao tamanho da mensagem;
- stickers tratados como fotografias;
- avatares inconsistentes;
- SSE montado somente quando Omnichannel está aberto;
- sons disparados por eventos que não são novas mensagens;
- sessão incorreta escolhida automaticamente;
- header excessivo;
- nomenclatura técnica;
- mobile desperdiçando grande parte da viewport.

---

# 7. MEDIA VIEWER

Criar renderer específico para:

~~~text
image
video
sticker
audio
document
~~~

Criar MediaViewer global para imagens e vídeos.

Imagem:

~~~text
expandir
zoom
pan
fit
download
fechar
ESC
~~~

Vídeo:

~~~text
expandir
player grande
requestFullscreen()
controls
download
~~~

Sticker:

~~~text
renderer próprio
128–160 px aproximadamente
sem background fotográfico
sem gradient
sem card pesado
sem tratamento como imagem normal
~~~

---

# 8. AVATARES

Criar componente único:

~~~text
ConversationAvatar
~~~

Responsável por:

~~~text
authenticated fetch
lazy loading
cache
error state
fallback visual
~~~

Cache por:

~~~text
tenant_id + session_id + contact_jid
~~~

Somente avatares próximos à viewport devem ser carregados.

O fallback com iniciais deve representar:

~~~text
avatar realmente inexistente
~~~

e não:

~~~text
avatar que o sistema decidiu não buscar
~~~

---

# 9. REALTIME GLOBAL

O realtime do WhatsApp não deve pertencer ao `OmnichannelView`.

Criar provider global montado dentro da aplicação autenticada:

~~~text
RealtimeProvider
├── WhatsApp events
├── Orders events
├── Event deduplication
├── Notification Engine
└── Sound Engine
~~~

Uma mensagem deve ser recebida mesmo se o usuário estiver em:

~~~text
Início
Pedidos
Clientes
Campanhas
Minha Empresa
Integrações
~~~

---

# 10. NOTIFICAÇÕES

Som principal somente para:

~~~text
message.created
AND incoming
AND event não processado anteriormente
~~~

Nunca tocar som para:

~~~text
read
played
delivered
reaction
media.ready
message.status.updated
outgoing
conversation.updated
~~~

Implementar Browser Notification API.

Quando a aplicação estiver em background:

~~~text
Maria
"Boa noite, quero fazer um pedido"
~~~

Clique na notificação:

~~~text
focar/abrir Dominus
→ Atendimento
→ sessão correta
→ conversa correta
~~~

Posteriormente implementar:

~~~text
PWA
Service Worker
Web Push
~~~

para notificações mesmo sem uma aba ativa.

---

# 11. ERROS E OBSERVABILIDADE PARA O USUÁRIO

Nenhum erro operacional importante deve existir somente em:

~~~text
console.warn
console.error
~~~

Eliminar `.catch(() => {})` em operações relevantes.

Criar contrato:

~~~ts
interface AppError {
  code: string;
  title: string;
  message: string;
  retryable: boolean;
  suggestedAction?: string;
  correlationId?: string;
}
~~~

Erros devem responder:

~~~text
O que aconteceu?
O que foi afetado?
Posso tentar novamente?
O usuário precisa fazer algo?
~~~

Problemas persistentes devem aparecer dentro da área afetada.

Toast será usado somente para eventos transitórios.

---

# 12. PRODUTO E LINGUAGEM

O Dominus não deve parecer um painel corporativo genérico.

Eliminar linguagem artificial como:

~~~text
Ambiente Interno Corporativo
Estação Corporativa
Governança & Parâmetros da Empresa
Dados Institucionais & Cultura
Diretrizes Financeiras & Pagamento
Whats API Sync
~~~

O sistema deverá utilizar linguagem direta de operação do negócio.

Menu alvo:

~~~text
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
~~~

`Project Hub` deve sair completamente da interface de tenants.

`Cases & Portfólio` poderá ser transformado em:

~~~text
Mais soluções
~~~

como área comercial discreta da Dominuslabs.

---

# 13. FUNCIONÁRIO DIGITAL

Não posicionar a tecnologia como "IA" para o usuário final.

O conceito de produto será:

~~~text
Funcionário Digital
~~~

Essa área deverá mostrar trabalho realizado:

~~~text
conversas atendidas
pedidos criados
clientes recuperados
vendas assistidas
status atual
~~~

E permitir configurar:

~~~text
como ele atende
tom de voz
o que pode fazer
quando chamar humano
limites
descontos
políticas
horários
~~~

Detalhes técnicos como:

~~~text
tokens
provider
modelo
LiteLLM
~~~

devem ficar em área avançada de custos/transparência.

---

# 14. MINHA EMPRESA

Substituir `Governança & Empresa` por:

~~~text
Minha Empresa
~~~

Estrutura:

~~~text
Dados da loja
Atendimento
Entrega
Pagamentos
Cardápio
Promoções
Políticas
~~~

Eliminar overflow horizontal da página.

No desktop, tabs horizontais devem possuir:

~~~text
seta esquerda
seta direita
fade lateral
scroll automático para aba ativa
~~~

No mobile, usar seletor/bottom sheet apropriado.

---

# 15. ORDER MANAGER

O Order Manager deve parecer uma central operacional real.

Priorizar:

~~~text
NOVOS
PREPARANDO
PRONTOS
EM ENTREGA
~~~

Cada pedido deve mostrar rapidamente:

~~~text
tempo desde criação
cliente
itens
total
pagamento
tipo de entrega
endereço
origem
ação principal
~~~

Indicadores operacionais:

~~~text
novos
atrasados
em preparo
faturamento hoje
tempo médio
~~~

Eliminar áreas vazias gigantes e controles visuais sem valor operacional.

---

# 16. DASHBOARD

Corrigir imediatamente métricas falsas.

`Pedidos Hoje` significa exclusivamente pedidos da data atual no timezone correto.

Se houver zero:

~~~text
0
~~~

Nunca utilizar histórico como fallback.

Filtros:

~~~text
Hoje
7 dias
30 dias
~~~

devem modificar efetivamente a consulta/métrica.

Nenhuma métrica poderá usar números hardcoded ou defaults demonstrativos.

---

# 17. MOBILE-FIRST REAL

O mobile não deverá ser desktop comprimido.

Criar shell próprio.

Bottom navigation:

~~~text
Início
Atendimento
Pedidos
Clientes
Mais
~~~

Eliminar sidebar desktop do mobile.

Omnichannel mobile:

~~~text
Lista de conversas
→ toca conversa
→ chat ocupa praticamente toda a tela
~~~

Usar:

~~~css
height: 100dvh;
padding-bottom: env(safe-area-inset-bottom);
~~~

Touch targets adequados.

Corrigir qualquer sobreposição entre:

~~~text
menu
logo
close button
headers
composer
~~~

---

# 18. PERFIL

Criar:

~~~text
Meu Perfil
~~~

Separado de `Minha Empresa`.

Campos e funções:

~~~text
nome
email
foto
senha
sessões autenticadas
preferências
notificações
som
idioma
tema
~~~

---

# 19. ARQUITETURA DE CÓDIGO

Evitar crescimento por anexação.

Arquivos monolíticos atuais devem ser decompostos por responsabilidade.

Arquivos identificados:

~~~text
OmnichannelView.tsx
CompanySettingsView.tsx
OrderManagerView.tsx
webhooks.py
n8n_service.py
session.manager.js
~~~

Pages devem coordenar componentes.

Não devem implementar simultaneamente:

~~~text
API
realtime
storage
media
notifications
business rules
UI complexa
~~~

Arquitetura-alvo para frontend:

~~~text
features/
├── omnichannel/
│   ├── components/
│   ├── hooks/
│   ├── api/
│   ├── state/
│   └── types/
├── orders/
├── customers/
├── company/
└── digital-worker/

realtime/
notifications/
shared/
design-system/
~~~

Arquitetura-alvo aproximada para Whats API:

~~~text
whatsapp/
├── session/
├── message/
├── media/
├── contacts/
├── groups/
├── sending/
└── events/
~~~

Arquitetura-alvo aproximada para backend Dominus:

~~~text
events/
├── schemas/
├── handlers/
├── router/
└── services/

integrations/
├── whatsapp/
├── n8n/
└── payments/

domains/
├── conversations/
├── orders/
├── customers/
├── company/
└── analytics/
~~~

A divisão deve acontecer por responsabilidade real, não por quantidade arbitrária de linhas.

---

# 20. UX MOBILE

O mobile deverá ser tratado como experiência própria.

Objetivo:

~~~text
menos chrome
mais conteúdo
ações alcançáveis
navegação semelhante a app
zero overflow horizontal
zero sobreposição
~~~

No Omnichannel:

~~~text
TELA 1
Conversas

TELA 2
Chat
~~~

Nunca tentar reproduzir simultaneamente no celular a disposição desktop completa.

---

# 21. PERFORMANCE

Implementar:

~~~text
cursor pagination
lazy avatars
lazy media
message virtualization quando necessária
conversation virtualization quando necessária
memoização de rows
AbortController
request deduplication
caching explícito
~~~

A aplicação deve continuar responsiva com:

~~~text
milhares de contatos
centenas de conversas
dezenas de milhares de mensagens
múltiplas sessões WhatsApp
~~~

---

# 22. DESIGN SYSTEM / FRONTEND SKILL

Criar skill específica do Dominus para agentes frontend.

Exemplo:

~~~text
.engine/skills/dominus-frontend/SKILL.md
~~~

Ela deverá definir:

- público do produto;
- objetivo do produto;
- design tokens;
- tipografia;
- spacing;
- breakpoints;
- navegação;
- mobile shell;
- desktop shell;
- formulários;
- tabelas;
- dialogs;
- media viewer;
- loading;
- empty states;
- error states;
- offline states;
- accessibility;
- touch targets;
- idioma e linguagem;
- padrões proibidos.

Regras mínimas da skill:

~~~text
Nunca usar linguagem corporativa artificial.

Nunca criar dado fake para preencher interface.

Nunca criar botão/controle visual sem função real.

Nunca esconder erro relevante no console.

Nunca resolver overflow horizontal da página com scrollbar como solução principal.

Nunca escolher uma sessão desconectada como fallback.

Nunca criar componente-page monolítico para uma feature grande.

Sempre validar mobile desde o início.

Sempre implementar estados:
loading
empty
success
partial
error
offline
permission denied
disconnected
~~~

---

# 23. TESTES

Criar validação Playwright nos breakpoints:

~~~text
375x812
390x844
414x896
768x1024
1366x768
1440x900
1920x1080
~~~

Fluxos obrigatórios:

~~~text
login
abrir menu mobile
fechar menu mobile
bottom navigation
lista de conversas
infinite scroll de conversas
abrir conversa
infinite scroll de mensagens antigas
nova mensagem em realtime
message.status.updated
garantir ausência de som em status update
browser notification
imagem expandida
vídeo expandido
fullscreen de vídeo
sticker
áudio
documento
avatar
sessão desconectada
nenhuma sessão disponível
erro de fetch
401
403
500
offline
retry
tabs Minha Empresa
Order Manager
Dashboard hoje sem pedidos
~~~

Asserções adicionais:

~~~text
horizontal overflow = 0
elementos fora da viewport = 0
controles sobrepostos = 0
dados fake = 0
fallback crítico = 0
~~~

---

# 24. CRITÉRIOS DE CONCLUSÃO

A missão só estará concluída quando:

- nenhum secret/config crítico possuir fallback funcional;
- nenhum valor real sensível/topológico desnecessário estiver hardcoded;
- nenhum dado demonstrativo for exibido como dado real;
- `Pedidos Hoje` usar somente pedidos da data atual;
- filtros de período modificarem dados reais;
- sessão desconectada nunca for selecionada silenciosamente;
- eventos possuírem tipo inequívoco;
- `message.status.updated` nunca for tratado como `message.created`;
- status de mensagem nunca disparar som principal;
- realtime do WhatsApp funcionar em toda a aplicação autenticada;
- browser notifications funcionarem fora do Omnichannel;
- conversas possuírem cursor pagination;
- mensagens possuírem cursor pagination;
- mensagens antigas carregarem sob demanda;
- conversas antigas carregarem sob demanda;
- avatares visíveis carregarem sob demanda;
- avatares usarem pipeline autenticado consistente;
- mídia do WhatsApp for persistida localmente;
- frontend não depender de URLs temporárias do WhatsApp;
- GET de mídia servir mídia persistida;
- falha de mídia possuir estado explícito;
- imagens puderem ser ampliadas;
- vídeos puderem ser ampliados e entrar em fullscreen;
- stickers possuírem renderer próprio;
- erros relevantes forem visíveis;
- mensagens de erro forem legíveis;
- ações corretivas forem sugeridas quando disponíveis;
- `Minha Empresa` não possuir overflow horizontal inadequado;
- tabs longas forem navegáveis sem scrollbar minúscula como mecanismo principal;
- mobile possuir shell próprio;
- sidebar desktop não for utilizada como navegação principal mobile;
- Omnichannel mobile utilizar corretamente a viewport;
- drawer não sobrepor logo ou controles;
- `Project Hub` não estiver presente para tenants;
- `Cases & Portfólio` for removido ou transformado em `Mais soluções`;
- existir página `Meu Perfil`;
- o conceito de IA for apresentado principalmente como `Funcionário Digital`;
- arquivos monolíticos principais forem decompostos por responsabilidade;
- testes E2E passarem nos breakpoints definidos;
- Zero Trust permanecer intacto;
- isolamento multi-tenant permanecer intacto;
- ownership de sessão permanecer obrigatório;
- nenhuma correção de UX reduzir segurança para facilitar funcionamento.

---

# 25. REGRA DE EXECUÇÃO PARA OS AGENTES

Antes de modificar qualquer fluxo:

1. Identificar o contrato atual.
2. Verificar todos os consumidores.
3. Verificar dependências entre os três repositórios e n8n.
4. Criar testes de regressão.
5. Implementar a mudança.
6. Remover somente código comprovadamente substituído.
7. Validar segurança.
8. Validar desktop.
9. Validar mobile.
10. Validar comportamento de erro.

Não utilizar:

~~~text
hardcode
mock em produção
fallback silencioso
catch vazio
sessão arbitrária
valor demonstrativo
dados inventados
duplicação de contratos
endpoint novo apenas para evitar refatoração correta
~~~

Se o sistema não possuir informação suficiente para executar uma operação corretamente, deve recusar a operação de forma clara em vez de fabricar uma resposta aparentemente funcional.