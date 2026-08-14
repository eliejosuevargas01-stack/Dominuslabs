# Evolução Arquitetural: De Aplicação Monolítica a Ecossistema Enterprise (2026+)

Este documento delineia a rota de migração da atual arquitetura do **Project Hub** (FastAPI, SQLite/Postgres em Coolify, React SPA) para uma arquitetura de "Ecossistema Empresarial Omnicanal" de alto nível, fundamentada nas práticas de governança, escalabilidade, inteligência artificial agêntica e conformidade normativa exigidas no mercado global e brasileiro (LGPD).

---

## 1. Infraestrutura e Arquitetura Tecnológica

### 1.1 Estado Atual (Monolito Moderno)
- **Backend:** Uma única aplicação FastAPI que gerencia usuários, projetos, integrações de webhook (n8n), upload de arquivos e banco de dados.
- **Frontend:** React SPA (Vite).
- **Implantação:** Docker Compose simples provisionado através da plataforma Coolify.
- **Armazenamento:** `Volume Mounts` para banco de dados SQLite (ou banco PostgreSQL na mesma rede) e arquivos persistentes.

### 1.2 Visão Enterprise (Microserviços & Event-Driven)
A evolução natural para lidar com volumes massivos de tráfego, isolamento de falhas e deploys independentes exige o particionamento do monolito.

*   **Separação por Domínio:** Quebrar o FastAPI em microserviços independentes:
    1.  `Identity & Access Management (IAM)`: Gerenciamento de tokens (OAuth2/OIDC), MTLS, RBAC.
    2.  `Project Management Service`: Regras de negócio core dos projetos.
    3.  `Integration & Webhook Service`: Processamento assíncrono para os endpoints do n8n/WhatsApp, protegendo o sistema core de lentidões de terceiros.
    4.  `File Manager Service`: Serviço dedicado com suporte a S3 ao invés de disco local, utilizando *presigned URLs*.
*   **Comunicação Assíncrona:** Introdução de um Message Broker corporativo (Kafka, RabbitMQ ou AWS SQS/EventBridge) para garantir que processos em lote (como scrapping ou envio de mensagens massivas via CRM) não criem gargalos na API transacional.
*   **Orquestração e Self-Healing:** Transição do Coolify/Docker Compose nativo para **Kubernetes (K8s)** (EKS, GKE, AKS) ou soluções serverless. K8s permitirá gerenciar Grupos de Autoescalonamento (ASG), Balanceadores de Carga Elásticos (ELB), e `liveness/readiness probes` para recuperação automática.
*   **Gestão de API (API Gateway):** Inserir um gateway avançado (ex: Kong, Apigee ou AWS API Gateway) à frente dos serviços, consolidando roteamento, *Rate Limiting*, observabilidade agregada, transformação de payload e autenticação unificada.

---

## 2. Padrões de Integração e Inteligência Artificial Agêntica (MCP)

### 2.1 Estado Atual
As integrações são feitas primariamente via webhooks (recebidos do n8n), e há a intenção de conversar com IA de maneira tradicional ou simples via API.

### 2.2 Visão Enterprise (Model Context Protocol - MCP)
A arquitetura de 2026 prevê uma mudança da conectividade frágil ponto a ponto para o padrão aberto **MCP**.
*   **Servidor MCP Nativo:** O Project Hub deverá expor uma interface MCP (via JSON-RPC sobre HTTP) ao invés de depender puramente de REST para agentes de IA.
*   **Ferramentas Controladas (Tools & Resources):**
    - `Tools`: Endpoints em que uma IA pode invocar a aprovação ou alteração de estado de um Projeto sob rigorosa política de Zero Trust.
    - `Resources`: Disponibilização da base de dados e documentos (via técnica RAG - Retrieval-Augmented Generation) para as inteligências analíticas.
*   **Governança de Automação:** Prevenção de alucinações de IA limitando as permissões criptográficas de quem acessa as APIs via MCP através de *scopes* estritos de OAuth 2.1 e fluxos PKCE, rastreáveis pelo Identity Provider da corporação.

---

## 3. Segurança Corporativa e Governança (Zero Trust)

### 3.1 Estado Atual
Uso de JWTs padrão com tempo de expiração prolongado, senhas com PBKDF2 HMAC-SHA256, e base local de usuários. A política de CORS é controlada via variáveis de ambiente.

### 3.2 Visão Enterprise
*   **Criptografia End-to-End e Repouso:** Adoção rigorosa de criptografia `AES-256` em repouso no banco de dados e nos sistemas de arquivos de upload. Criptografia transparente dos campos sensíveis (PII - *Personally Identifiable Information*).
*   **Isolamento Multi-Tenant:** Atualmente os dados são particionados de forma lógica (coluna `tenant_id`). Para clientes hiper-regulados, deverá se oferecer Isolamento Físico (um schema por cliente, ou uma instância de banco por cliente).
*   **Rotação Dinâmica de Segredos:** Migrar variáveis de ambiente de banco de dados (`DATABASE_URL`) e `JWT_SECRET` de arquivos estáticos `.env` para cofres corporativos dinâmicos como **HashiCorp Vault** ou **AWS Secrets Manager**, com rotação automática.
*   **Auditoria Rigorosa (Audit Trails):** Todas as mutações do banco de dados e acessos críticos devem gerar logs inalteráveis repassados a um sistema de SIEM (ex: Splunk, Datadog, ELK).

---

## 4. Governança Regulatória e Conformidade: LGPD e GDPR

### 4.1 Estado Atual
A aplicação coleta e processa dados sem a presença imediata de mecânicas de "expurgação automática" baseada em temporalidade e bases legais.

### 4.2 Visão Enterprise
Dada a severidade da fiscalização da Autoridade Nacional de Proteção de Dados (ANPD):
*   **Data Mapping Integrado:** O banco deve possuir anotações/tags em nível de ORM (SQLAlchemy) determinando quais colunas são classificadas como "Sensíveis", disparando rotinas automáticas de anonimização ou expurgo.
*   **Direito ao Esquecimento:** Fornecimento nativo de APIs assíncronas que permitam aos usuários solicitarem a deleção definitiva de seus rastros. Se existirem dados financeiros (que obrigam armazenamento prolongado), técnicas de *Soft-Delete/Data Masking* criptográfico devem ser acionadas.
*   **Consentimento Explícito:** Versionamento de aceites de Termos de Uso acoplados a hash criptográfico garantindo o registro legal do consentimento (Registro em WORM storage).

---

## 5. Qualidade e Resiliência (SLAs de "Cinco Noves" - 99.999%)

### 5.1 Estado Atual
Tempo de resposta dependente de disco rígido da VM e recursos provisionados de um nó único do Coolify. Falhas de hardware no servidor físico causariam *downtime*.

### 5.2 Visão Enterprise
*   **Disponibilidade Geográfica Ativa-Ativa:** Implementar o banco de dados como *CockroachDB* ou *Amazon Aurora Global* e distribuir clusters de aplicação através de múltiplas Zonas de Disponibilidade (AZs) e até múltiplas regiões.
*   **Estratégia de Cache Aggressive:** Utilização de instâncias Redis/Memcached em memória para respostas sub-milissegundos e *Rate Limiting* distribuído, poupando as queries do banco relacional principal.
*   **Observabilidade e WEM:** Integrar ferramentas avançadas para métricas de APM (Application Performance Monitoring) focado em latência conversacional (SLA esperado: <500ms). Adicionalmente, métricas do *Workforce Engagement Management* precisam estar inseridas nos painéis para controle de qualidade da performance analítica do time que usar o sistema, combatendo ativamente o custo oculto na rotatividade (turnover) do suporte.
