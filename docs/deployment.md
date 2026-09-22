# Deploy e Operacao

Documentacao completa de deploy, infraestrutura e operacao do DominusLabs.

---

## 1. Visao Geral da Infraestrutura

A stack roda em um unico VPS com os seguintes componentes:

| Componente | Descricao |
|------------|-----------|
| VPS | 72.60.247.157 (SSH porta 2222, usuario root) |
| Orquestrador | Coolify self-hosted (painel web) |
| Proxy Reverso | Traefik (gerenciado pelo Coolify) |
| Banco de Dados | PostgreSQL (container `coolify-db`) |
| Aplicacoes | Containers Docker gerenciados pelo Coolify |
| SSL | Let's Encrypt automatico via Traefik |

Fluxo de requisicao:

```
Usuario -> DNS (dominuslabs.online / whats.dominuslabs.online)
    -> Traefik (Coolify) -> Container da aplicacao
```

---

## 2. Aplicacoes

| Nome | App ID | Git Repo | URL | Container Padrao |
|------|--------|----------|-----|-----------------|
| DominusLabs (backend + frontend) | 38 | `github.com:eliejosuevargas01-stack/Dominuslabs.git` (branch `main`) | https://dominuslabs.online | `sjrweu7rw8e3nywm5stef2ri-*` |
| WA API | 32 | `github.com:eliejosuevargas01-stack/api_whatsapp_v1.2.git` (branch `main`) | https://whats.dominuslabs.online | `hkossco0sggwwwss0cwk4w0s-*` |

---

## 3. Processo de Deploy Normal

1. **Push no Git**
   ```bash
   git add .
   git commit -m "feat: nova funcionalidade"
   git push origin main
   ```

2. **Coolify detecta o push**
   - Via webhook automatico do GitHub, ou
   - Manualmente pelo painel Coolify

3. **Build do container**
   - Coolify executa o build conforme o Dockerfile do repositorio
   - DominusLabs: `npm run build` (frontend) + `uvicorn` (backend)
   - WA API: build do Node.js

4. **Health check**
   - Coolify aguarda o novo container responder ao health check
   - Start period: 30s
   - Se falhar, o deploy e marcado como falho

5. **Troca de trafego**
   - Container antigo e parado
   - Proxy reverso roteia trafego para o novo container

---

## 4. Deploy via CLI

Quando o painel web nao esta disponivel ou para automatizacao.

### App 38 — DominusLabs

```bash
ID=$(ssh -p 2222 root@72.60.247.157 "docker exec coolify-db psql -U coolify -d coolify -t -A -c \"INSERT INTO application_deployment_queues (application_id, deployment_uuid, status, is_webhook, created_at, updated_at) VALUES ('38', gen_random_uuid()::text, 'in_progress', false, now(), now()) RETURNING id\"")
ssh -p 2222 root@72.60.247.157 "docker exec coolify php artisan tinker --execute='dispatch(new App\\\\Jobs\\\\ApplicationDeploymentJob($ID));'"
```

### App 32 — WA API

```bash
ID=$(ssh -p 2222 root@72.60.247.157 "docker exec coolify-db psql -U coolify -d coolify -t -A -c \"INSERT INTO application_deployment_queues (application_id, deployment_uuid, status, is_webhook, created_at, updated_at) VALUES ('32', gen_random_uuid()::text, 'in_progress', false, now(), now()) RETURNING id\"")
ssh -p 2222 root@72.60.247.157 "docker exec coolify php artisan tinker --execute='dispatch(new App\\\\Jobs\\\\ApplicationDeploymentJob($ID));'"
```

---

## 5. Volumes Persistentes

| App | Path no Host | Path no Container | Conteudo |
|-----|-------------|-------------------|----------|
| WA API (32) | `coolify_volumes/hkossco0sggwwwss0cwk4w0s/sessions` | `/app/sessions` | Credenciais Baileys por sessao (sessoes WhatsApp) |
| WA API (32) | `coolify_volumes/hkossco0sggwwwss0cwk4w0s/data` | `/app/data` | Midia, mensagens e conversas |
| WA API (32) | `coolify_volumes/hkossco0sggwwwss0cwk4w0s/keys` | `/app/keys` | Chaves JWT para autenticacao da API |

> **Nota:** DominusLabs (App 38) nao utiliza volumes persistentes customizados. Todo estado res no banco de dados PostgreSQL.

---

## 6. Variaveis de Ambiente Criticas

### Backend — DominusLabs (App 38)

| Variavel | Descricao |
|----------|-----------|
| `DATABASE_URL` | URI de conexao com PostgreSQL (`postgresql://user:pass@host:5432/DOMINUS_DB`) |
| `SECRET_KEY` | Chave JWT para autenticacao de usuarios |
| `WHATSAPP_API_URL` | URL da WA API: `https://whats.dominuslabs.online` |
| `WHATSAPP_API_PRIVATE_KEY_PATH` | Caminho da chave privada: `/app/keys/private.pem` |
| `N8N_WEBHOOK_URL` | Webhook do n8n: `https://myn8n.seommerce.shop/webhook/lead_responses` |

### WA API (App 32)

| Variavel | Descricao |
|----------|-----------|
| `PG_CONNECTION_STRING` | URI de conexao com PostgreSQL (`postgresql://user:pass@host:5430/whats_api`) |
| `PORT` | Porta da aplicacao (`3000`) |
| `SESSIONS_DIR` | Diretorio de sessoes Baileys (`/app/sessions`) |
| `DATA_DIR` | Diretorio de dados (`/app/data`) |
| `MEDIA_DIR` | Diretorio de midia (`/app/data/media`) |
| `KEYS_DIR` | Diretorio de chaves JWT (`/app/keys`) |
| `AUTO_CONNECT` | Reconectar sessoes automaticamente (`true`) |
| `N8N_WEBHOOK_URL` | Webhook do n8n: `https://myn8n.seommerce.shop/webhook/lead_responses` |
| `N8N_WEBHOOK_SECRET` | Chave HMAC para validar webhooks do n8n |
| `N8N_WEBHOOK_ENABLED` | Habilitar envio de webhooks (`true`) |
| `TYPING_DELAY_ENABLED` | Simular digitacao antes de enviar mensagens (`true`) |
| `LOG_LEVEL` | Nivel de logs (`info`) |

---

## 7. Health Checks

| App | Endpoint | Metodo | Resposta Esperada | Configuracao |
|-----|----------|--------|-------------------|--------------|
| DominusLabs (38) | `/api/v1/openapi.json` | GET | `200 OK` | Interval: 10s, Timeout: 5s, Retries: 3, Start Period: 30s |
| WA API (32) | `/api/health` | GET | `200 OK` com `{status: "ok"}` | Interval: 10s, Timeout: 5s, Retries: 3, Start Period: 30s |

**Comportamento:**
- O health check decide quando o container esta pronto para receber trafego
- Se falhar 3 vezes consecutivas, o deploy e considerado falho
- Durante o `start_period` de 30s, falhas sao ignoradas (tempo de warm-up)
- Container nao saludavel nao recebe trafego do proxy

---

## 8. Rollback

### Via Painel Coolify

1. Acesse o painel Coolify
2. Selecione a aplicacao
3. V para a aba **Deployments**
4. Selecione o deploy anterior desejado
5. Clique em **Redeploy**

### Via CLI

Alterar `force_rebuild=false` e apontar para o commit anterior. Exemplo:

```bash
# Listar deploys anteriores
ssh -p 2222 root@72.60.247.157 "docker exec coolify-db psql -U coolify -d coolify -c \"SELECT deployment_uuid, status, created_at FROM application_deployment_queues WHERE application_id = '38' ORDER BY created_at DESC LIMIT 5\""

# Redeploy de um commit anterior (substituir COMMIT_HASH)
ssh -p 2222 root@72.60.247.157 "docker exec coolify-db psql -U coolify -d coolify -c \"UPDATE applications SET git_commit = 'COMMIT_HASH' WHERE id = '38'\""
```

> Coolify mantem as imagens Docker dos containers anteriores, permitindo rollback rapido.

---

## 9. Banco de Dados

### Acesso

O PostgreSQL roda dentro do container `coolify-db` e e usado por todas as aplicacoes.

```bash
# Acessar PostgreSQL via SSH
ssh -p 2222 root@72.60.247.157 "docker exec coolify-db psql -U coolify -d coolify"
```

### Migrations

| App | Ferramenta | Comando |
|-----|-----------|---------|
| DominusLabs (backend) | Alembic | `alembic upgrade head` (executado automaticamente no build) |
| WA API | db.js (scripts SQL) | Verificar scripts no repositorio da API |

### Backup

> **PENDENTE:** Backup automatico nao esta configurado.

```bash
# Backup manual (exemplo)
ssh -p 2222 root@72.60.247.157 "docker exec coolify-db pg_dump -U coolify -d coolify > /tmp/coolify-backup-$(date +%F).sql"
```

---

## 10. SSH no VPS

### Acesso

```bash
ssh -p 2222 root@72.60.247.157
```

### Comandos Uteis

```bash
# Listar containers em execucao
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logs de um container em tempo real
docker logs -f <container_name>

# Executar comando dentro de um container
docker exec -it <container_name> sh

# Restart de um container
docker restart <container_name>

# Info do container da App 38
docker ps --filter "name=sjrweu7rw8e3nywm5stef2ri"

# Info do container da App 32
docker ps --filter "name=hkossco0sggwwwss0cwk4w0s"

# Verificar health check via curl (de dentro do VPS)
docker exec <app_container> curl -f http://localhost:PORT/endpoint

# Acessar banco diretamente
docker exec -it coolify-db psql -U coolify -d coolify

# Espaco em disco
df -h

# Uso de recursos dos containers
docker stats --no-stream
```

---

*Ultima atualizacao: 2026-09-22*
