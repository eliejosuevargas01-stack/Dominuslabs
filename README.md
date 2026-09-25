# Dominuslabs

> **Status:** CANONICAL — Target Architecture

Dominus é um funcionário digital e sistema operacional para pequenos e médios negócios que atende clientes, vende, recebe pedidos, cobra, acompanha entregas, fideliza clientes, executa campanhas e fornece inteligência comercial — sem obrigar o usuário a entender IA, APIs, webhooks, infraestrutura ou terminologia corporativa artificial.

---

## Product Concept

Dominus é uma plataforma SaaS multi-tenant que funciona como:

- **Funcionário Digital**: Atendimento automático inteligente via WhatsApp
- **Central de Pedidos**: Gerenciamento completo de delivery e retirada
- **CRM Omnichannel**: Histórico de conversas e clientes em um só lugar
- **Inteligência Comercial**: Métricas e analytics em tempo real

---

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│   Dominus    │────▶│    IDPW     │
└─────────────┘     │  (Backend)   │     │  (M2M JWT)  │
                    └──────┬───────┘     └─────────────┘
                           │                    │
                           ▼                    │
                    ┌──────────────┐            │
                    │   Frontend   │            │
                    │   (React)    │            │
                    └──────────────┘            │
                           ▲                    │
                           │                    │
                    ┌──────┴───────┐◀───────────┘
                    │  Whats API   │
                    │ (Resource    │
                    │   Server)    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │     n8n      │
                    │ (Automation) │
                    └──────────────┘
```

### Trust Boundaries

| Serviço | Função | Autoridade |
|---------|--------|------------|
| **Dominus** | Business control plane | Autenticação humana, tenant, permissões, regras de negócio |
| **IDPW** | M2M Identity Provider | Emissão de JWT RS256 de curta duração |
| **Whats API** | Resource Server | Sessões, mensagens, mídia, contatos WhatsApp |
| **n8n** | Event router | Automações e workflows |

---

## Repositories

| Repositório | Descrição | Função |
|-------------|-----------|--------|
| `Dominuslabs` | Backend + Frontend | Produto principal, API REST, interface web |
| `IDC_Dominuslabs` | IDPW | M2M Identity Provider, JWT issuance authority |
| `api_whatsapp_v1.2` | Whats API | WhatsApp Resource Server, Baileys |

---

## Key Concepts

### Zero Trust Architecture

O browser **NUNCA**:
- Recebe JWT M2M
- Recebe private keys
- Conhece credenciais internas
- Decide tenant_id confiável
- Acessa Whats API diretamente como autoridade

### Fluxo de Autenticação

```
Browser → Dominus → Autenticação humana
                   → Resolução server-side de tenant
                   → Solicitação de JWT M2M ao IDPW
                   → WhatsAppClient interno
                   → Whats API
```

### Event Contract

Eventos assíncronos utilizam contrato único:

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

---

## Local Development

### Pré-requisitos

- Python 3.12+
- Node.js 24+
- PostgreSQL 15+

### Setup

```bash
# Backend
cd project-hub/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd project-hub/frontend
npm ci
npm run dev
```

---

## Configuration

Variáveis de ambiente obrigatórias:

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | URL de conexão PostgreSQL |
| `JWT_SECRET` | Chave JWT para autenticação humana |
| `IDPW_URL` | URL do IDPW |
| `IDPW_JWKS_URL` | URL do JWKS do IDPW |
| `DOMINUS_PRIVATE_KEY` | Chave privada RSA para IDPW |
| `WHATSAPP_API_URL` | URL da Whats API |
| `WHATS_API_PUBLIC_KEY` | Chave pública da Whats API |

`.env.example` documenta nomes e formatos. Valores reais são fornecidos por secret manager.

---

## Tests

```bash
# Backend
pytest

# Frontend
npm run test

# E2E
npx playwright test
```

---

## Documentation

### Canonical Sources

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `docs/refoundation/GOAL.md` | CANONICAL | Visão e princípios |
| `docs/refoundation/CONTRACTS.md` | CANONICAL | Contratos de arquitetura |
| `INTEGRATION_GUIDE.md` | CANONICAL | Guia de integração M2M |

### Architecture

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `docs/architecture.md` | CANONICAL | Visão geral da arquitetura |

### External Services

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `IDC_Dominuslabs/README.md` | CANONICAL | Documentação do IDPW |
| `api_whatsapp_v1.2/README.md` | CANONICAL | Documentação da Whats API |

### Historical

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `docs/refoundation/BASELINE.md` | HISTORICAL | Baseline do sistema |
| `docs/refoundation/FALLBACK_AUDIT.md` | HISTORICAL | Auditoria de fallbacks |
| `docs/refoundation/EVT_CATALOG.md` | HISTORICAL | Catálogo de eventos |

---

## License

Proprietary — Dominuslabs © 2026
