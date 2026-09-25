# Deploy e Operação

> **Status:** CANONICAL — Deployment Guide

Este documento descreve conceitos genéricos de deployment. Detalhes específicos de infraestrutura são mantidos em runbooks privados.

---

## Visão Geral da Infraestrutura

### Componentes

| Componente | Descrição |
|------------|-----------|
| Orquestrador | Coolify self-hosted |
| Proxy Reverso | Traefik |
| Banco de Dados | PostgreSQL |
| Aplicações | Containers Docker |
| SSL | Let's Encrypt automático |

### Fluxo de Requisição

```
Usuário → DNS → Traefik → Container da aplicação
```

---

## Aplicações

| Nome | Git Repo | Stack |
|------|----------|-------|
| Dominuslabs | Dominuslabs | FastAPI + React |
| Whats API | api_whatsapp_v1.2 | Node.js + Baileys |

---

## Processo de Deploy

### Via Painel Web

1. Acesse painel do orquestrador
2. Selecione aplicação
3. Clique em Deploy
4. Acompanhe logs em tempo real

### Via Git Push

Push para branch principal dispara build automático (webhook).

---

## Variáveis de Ambiente

### Dominuslabs (Backend)

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | URI PostgreSQL |
| `JWT_SECRET` | Chave JWT sessão humana |
| `IDPW_URL` | URL do IDPW |
| `IDPW_JWKS_URL` | URL JWKS |
| `DOMINUS_PRIVATE_KEY` | Chave privada RSA |
| `WHATSAPP_API_URL` | URL Whats API |
| `WHATS_API_PUBLIC_KEY` | Chave pública Whats API |
| `N8N_WEBHOOK_SECRET` | Segredo HMAC |

### Whats API

| Variável | Descrição |
|----------|-----------|
| `PG_CONNECTION_STRING` | URI PostgreSQL |
| `JWT_ISSUER` | Issuer IDPW |
| `IDPW_JWKS_URL` | URL JWKS |
| `WHATS_API_PRIVATE_KEY` | Chave privada |
| `DOMINUS_PUBLIC_KEY` | Chave pública Dominus |
| `SESSIONS_DIR` | Diretório sessões |
| `MEDIA_DIR` | Diretório mídia |
| `WEBHOOK_SECRET` | Segredo HMAC |

---

## Health Checks

| App | Endpoint | Resposta |
|-----|----------|----------|
| Dominuslabs | `/api/v1/openapi.json` | 200 OK |
| Whats API | `/api/health` | 200 OK + `{status: "ok"}` |

### Configuração

- Interval: 10s
- Timeout: 5s
- Retries: 3
- Start Period: 30s

---

## Rollback

### Via Painel

1. Acessar painel do orquestrador
2. Selecionar aplicação
3. Ir para Deployments
4. Selecionar deploy anterior
5. Clique em Redeploy

---

## Banco de Dados

### Migrations

| App | Ferramenta | Comando |
|-----|-----------|---------|
| Dominuslabs | Alembic | `alembic upgrade head` |
| Whats API | PostgreSQL scripts | Verificar scripts no repo |

### Backup

> **Nota:** Backup automático deve ser configurado. Verificar runbook privado.

---

## Volumes Persistentes

| App | Path Container | Conteúdo |
|-----|---------------|----------|
| Whats API | `/app/sessions` | Credenciais Baileys |
| Whats API | `/app/data` | Mídia, mensagens |
| Whats API | `/app/keys` | Chaves JWT |

> **Nota:** Dominus Labs não utiliza volumes persistentes customizados. Todo estado reside no banco de dados PostgreSQL.

---

## Segurança

### Princípios

1. **Sem dados sensíveis em repositórios públicos**
   - IPs, ports, SSH users
   - Container IDs, App IDs
   - URLs operacionais privadas
   - Tokens, secrets

2. **Secrets por Secret Manager**
   - Nunca em código
   - Nunca em Dockerfile
   - Nunca em logs

3. **Network Isolation**
   - Containers não expõem portas no host
   - Proxy é o único ponto de entrada

---

## Runbooks Privados

Informação operacional específica é mantida em runbooks privados:

- IPs e ports reais
- SSH access
- Container names específicos
- Comandos de administração
- URLs internas
- Credenciais específicas
- Procedimentos de disaster recovery

Consulte a equipe de DevOps para acesso.

---

## Referências

- `docs/architecture.md` — Arquitetura geral
- `docs/refoundation/GOAL.md` — Princípios
- `INTEGRATION_GUIDE.md` — Integração M2M
