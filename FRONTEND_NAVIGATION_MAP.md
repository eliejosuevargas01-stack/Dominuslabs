# MAPA DE NAVEGAÇÃO DO FRONTEND (FRONTEND NAVIGATION MAP)

Este documento descreve detalhadamente a navegação visual do frontend, página por página, para que o Playwright ou outras ferramentas de testes automatizados de UI consigam navegar pelas telas de forma inteligente.

## Login
- **URL/Rota:** `/login`
- **Layout / Elementos Principais:** Tela de autenticação centralizada, com branding da Dominuslabs, campo para senha e botão de acesso rápido.
- **Campos de Formulário:**
  - Nome: **Master Password** | Tipo: `password` | Placeholder: *'••••••••'* `data-testid="password-input"`
- **Botões:**
  - Texto: **'Acessar Plataforma'** | Local: *Abaixo do campo de senha* | Ação: Envia as credenciais para autenticação.
- **Sidebar (Menu Lateral):**
  - (Sem menu lateral - Tela Pública/Layout Limpo)
- **Fluxo de Navegação:** Após fazer login com sucesso, o sistema redireciona para a rota padrão ('/dashboard-operacional' ou similar dependendo da configuração de fallback).
- **Estados Especiais:** Loading state no botão (spinner e desabilitado) enquanto a requisição ocorre. Toasts exibem sucesso ou mensagem de erro (ex: 'Credenciais inválidas').

---

## Dashboard Operacional
- **URL/Rota:** `/dashboard-operacional`
- **Layout / Elementos Principais:** Visão geral da operação. Apresenta métricas (Receita Mensal, Novos Leads, Taxa de Conversão, MRR Ativo) no topo e gráficos/tabelas abaixo.
- **Campos de Formulário:**
  - (Sem campos de formulário relevantes identificados nesta visão geral)
- **Botões:**
  - Texto: **'Exportar Relatório'** | Local: *Canto superior direito* | Ação: Abre opções para exportar os dados do dashboard.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Página inicial após o login. A partir daqui, usar a sidebar para navegar para outras áreas.
- **Estados Especiais:** Loading visual (skeleton loaders) ao carregar métricas; Toasts para erros de carregamento.

---

## CRM / Pipeline
- **URL/Rota:** `/crm`
- **Layout / Elementos Principais:** Quadro Kanban com colunas representando estágios de vendas (Lead Novo, Em Contato, Proposta, Negociação, Fechado). Cartões representam os leads.
- **Campos de Formulário:**
  - Nome: **Busca de Leads** | Tipo: `text` | Placeholder: *'Buscar por nome, email ou telefone...'* `data-testid="search-leads"`
- **Botões:**
  - Texto: **'+ Novo Lead'** | Local: *Canto superior direito* | Ação: Abre o modal de criação de lead.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Clicar em um cartão de lead abre o painel lateral (Slide-over) com os detalhes do lead e permite edição. Opcionalmente, pode redirecionar para a visualização detalhada em `/crm/leads/:id`.
- **Estados Especiais:** Drag and drop (arrastar) dos cartões salva automaticamente. Toast notifica o sucesso da mudança de status.

---

## Detalhes do Lead
- **URL/Rota:** `/crm/leads/:id`
- **Layout / Elementos Principais:** Visão focada de um lead específico. Mostra informações de contato, histórico de interações, e campos personalizados associados.
- **Campos de Formulário:**
  - Nome: **Nome** | Tipo: `text` | Placeholder: *'Nome do lead'*
  - Nome: **Email** | Tipo: `email` | Placeholder: *'Email do lead'*
  - Nome: **Telefone** | Tipo: `text` | Placeholder: *'Telefone do lead'*
- **Botões:**
  - Texto: **'Salvar Alterações'** | Local: *Canto superior direito / inferior* | Ação: Salva as edições do lead.
  - Texto: **'Voltar'** | Local: *Canto superior esquerdo* | Ação: Retorna para o CRM.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Salvar as alterações exibe um toast e mantém o usuário na página. Clicar em voltar retorna para `/crm`.
- **Estados Especiais:** Modo de edição vs. visualização. Toasts de sucesso ou falha ao salvar.

---

## Omnichannel (Chat)
- **URL/Rota:** `/omnichannel`
- **Layout / Elementos Principais:** Interface de chat. Lista de conversas na esquerda (usuários/clientes) e área de mensagens na direita.
- **Campos de Formulário:**
  - Nome: **Nova Mensagem** | Tipo: `text` | Placeholder: *'Digite sua mensagem...'* `data-testid="message-input"`
- **Botões:**
  - Texto: **'Enviar'** | Local: *Canto inferior direito (ao lado do input)* | Ação: Envia a mensagem ao contato.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Selecionar um contato na lista atualiza o painel principal com o histórico de chat.
- **Estados Especiais:** Mensagens recebidas via SSE/WebSocket atualizam em tempo real. Notificações de falha de envio.

---

## Configurações da Empresa
- **URL/Rota:** `/settings`
- **Layout / Elementos Principais:** Formulário longo com abas ou seções para configurar os dados gerais, marca e preferências do sistema.
- **Campos de Formulário:**
  - Nome: **Nome da Empresa** | Tipo: `text` | Placeholder: *'Ex: Dominuslabs'*
  - Nome: **Fuso Horário** | Tipo: `select` | Placeholder: *'Selecione...'*
- **Botões:**
  - Texto: **'Salvar Configurações'** | Local: *Final do formulário / canto superior direito* | Ação: Salva os dados corporativos e atualiza a aplicação.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Salvar as configurações persiste as informações, geralmente sem redirecionar.
- **Estados Especiais:** Feedback visual ao salvar (loading no botão, toast de sucesso).

---

## Conexões
- **URL/Rota:** `/connections`
- **Layout / Elementos Principais:** Lista ou grid de integrações de terceiros (WhatsApp, Email, Ferramentas). Mostra o status (conectado, desconectado, erro).
- **Campos de Formulário:**
  - (Sem campos de formulário relevantes identificados nesta visão geral)
- **Botões:**
  - Texto: **'Conectar'** | Local: *No cartão de cada integração* | Ação: Inicia o fluxo de autenticação da integração (ex: QR Code para WhatsApp).
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Ao clicar em Conectar, um modal ou nova guia pode ser aberta. Em caso de QR Code, um modal exibe o código para escaneamento.
- **Estados Especiais:** Modal de QR Code (WhatsApp). Modais de confirmação para desconectar.

---

## Automações
- **URL/Rota:** `/automacoes`
- **Layout / Elementos Principais:** Painel de regras e fluxos automatizados. Pode apresentar uma lista de regras ativas ou uma tela de construção de fluxos.
- **Campos de Formulário:**
  - (Sem campos de formulário relevantes identificados nesta visão geral)
- **Botões:**
  - Texto: **'Nova Automação'** | Local: *Canto superior direito* | Ação: Inicia a criação de um novo fluxo (gatilhos e ações).
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Criar nova automação pode abrir um modal complexo ou navegar para um construtor de tela cheia.
- **Estados Especiais:** Ativar/desativar automação (toggles) com resposta imediata.

---

## Campanhas Wizard
- **URL/Rota:** `/campanhas-wizard`
- **Layout / Elementos Principais:** Fluxo em etapas (wizard) para criar novas campanhas de marketing ou de mensagens.
- **Campos de Formulário:**
  - Nome: **Nome da Campanha** | Tipo: `text` | Placeholder: *'Nome interno da campanha'*
- **Botões:**
  - Texto: **'Próximo'** | Local: *Inferior direito* | Ação: Avança para a próxima etapa do wizard.
  - Texto: **'Voltar'** | Local: *Inferior esquerdo* | Ação: Retorna à etapa anterior.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** O usuário preenche etapa por etapa. No último passo, um botão 'Lançar Campanha' (ou similar) finaliza e retorna à lista de campanhas ou dashboard.
- **Estados Especiais:** Validação de campos obrigatórios bloqueia o avanço (Next).

---

## Inteligência IA
- **URL/Rota:** `/ia-inteligencia`
- **Layout / Elementos Principais:** Configuração dos agentes de inteligência artificial. Opções para definir tom de voz, base de conhecimento e prompts.
- **Campos de Formulário:**
  - Nome: **Contexto do Agente** | Tipo: `textarea` | Placeholder: *'Descreva o comportamento do agente...'*
- **Botões:**
  - Texto: **'Atualizar Treinamento'** | Local: *Fim do bloco de texto* | Ação: Envia os dados atualizados para recriar ou atualizar o modelo local/remoto.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Salvar as configurações persiste as informações, mantendo na mesma tela.
- **Estados Especiais:** Exibição de métricas de uso da IA (tokens). Loading ao salvar.

---

## Admin Dashboard / Project Hub
- **URL/Rota:** `/project-hub`
- **Layout / Elementos Principais:** Painel de administração central (muitas vezes exibido apenas para super admins). Lista de projetos e acessos globais.
- **Campos de Formulário:**
  - (Sem campos de formulário relevantes identificados nesta visão geral)
- **Botões:**
  - Texto: **'Novo Projeto'** | Local: *Superior direito* | Ação: Abre o modal de criação de um novo projeto (tenant).
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Selecionar um projeto navega para os detalhes do mesmo (`/project-hub/project/:id`).
- **Estados Especiais:** Modais de confirmação.

---

## Detalhes do Projeto (Admin)
- **URL/Rota:** `/project-hub/project/:id`
- **Layout / Elementos Principais:** Gerenciamento específico de um projeto (cliente) a partir da visão de super admin.
- **Campos de Formulário:**
  - (Sem campos de formulário relevantes identificados nesta visão geral)
- **Botões:**
  - Texto: **'Suspender Projeto'** | Local: *Área de ações de perigo (Danger Zone)* | Ação: Bloqueia o acesso do tenant.
- **Sidebar (Menu Lateral):**
  - Ícones padrão para cada seção.
  - Item: **Dashboard**
  - Item: **CRM / Pipeline**
  - Item: **Omnichannel**
  - Item: **Campanhas (Wizard)**
  - Item: **Inteligência IA**
  - Item: **Automações**
  - Item: **Conexões**
  - Item: **Configurações**
  - Item: **Cases**
- **Fluxo de Navegação:** Voltar à lista através de breadcrumbs ou sidebar.
- **Estados Especiais:** Confirmações fortes (digitar o nome do projeto) antes de deletar ou suspender.

---

## Visualização Pública do Projeto
- **URL/Rota:** `/project/:public_token`
- **Layout / Elementos Principais:** Visualização de status ou apresentação (showcase) de um projeto para visitantes sem login. Focado em leitura.
- **Campos de Formulário:**
  - (Sem campos de formulário relevantes identificados nesta visão geral)
- **Botões:**
  - (Sem botões principais identificados)
- **Sidebar (Menu Lateral):**
  - (Sem menu lateral - Tela Pública/Layout Limpo)
- **Fluxo de Navegação:** Nenhuma navegação complexa; tela de leitura.
- **Estados Especiais:** Se o token for inválido, exibe tela de 'Projeto não encontrado'.

---

## Showcase / Casos de Sucesso
- **URL/Rota:** `/cases`
- **Layout / Elementos Principais:** Grid público ou interno mostrando portfólio/cases de sucesso. Cards com imagens, títulos e resultados.
- **Campos de Formulário:**
  - (Sem campos de formulário relevantes identificados nesta visão geral)
- **Botões:**
  - Texto: **'Ver Mais'** | Local: *Dentro de cada card de case* | Ação: Abre um modal ou expande as informações detalhadas do case.
- **Sidebar (Menu Lateral):**
  - (Sem menu lateral - Tela Pública/Layout Limpo)
- **Fluxo de Navegação:** Página pública sem sidebar quando acessada na raiz, ou interna via '/cases-dashboard' com sidebar.
- **Estados Especiais:** Imagens de alta resolução exibidas dinamicamente.

---

## Componentes Globais

### Sidebar (Sidebar.tsx)
- **Navegação Global:** Fornece atalhos diretos para `/dashboard-operacional`, `/crm`, `/omnichannel`, `/campanhas-wizard`, `/ia-inteligencia`, `/automacoes`, `/connections`, `/settings` e `/cases-dashboard`.
- **Interações:** Botão de colapsar (minimizar menu lateral). Salva preferência no `localStorage` (`sidebar_collapsed`). Botão de 'Sair' destrói tokens e leva a `/login`.

### Footer (Footer.tsx)
- **Rodapé:** Exibido em contextos específicos, contém links institucionais e informações de direitos autorais. Não contém ações críticas de fluxo principal.

### App (App.tsx)
- **Roteador Principal:** Gerencia `ProtectedRoute`, assegurando que rotas internas redirecionem para `/login` se o `admin_token` estiver ausente. Renderiza também o componente Header móvel com controle global.
