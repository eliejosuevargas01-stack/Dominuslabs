# Auditoria de Documentação — Dominus Ecosystem

> **Status:** HISTORICAL / AUDIT ARTIFACT  
> **Data original:** 2026-09-25  
> **Security note:** este arquivo preserva as conclusões da auditoria sem repetir IPs, hostnames operacionais, IDs de workflow/container ou outros detalhes de deployment.

## Objetivo

Identificar documentação canônica, documentação histórica e arquivos que precisavam ser reescritos para o Dominus Product & Architecture Refoundation.

Este relatório **não é fonte de arquitetura**. Use:

1. `docs/refoundation/GOAL.md`
2. `docs/refoundation/CONTRACTS.md`
3. `docs/architecture.md`
4. `docs/refoundation/PLAN.md`
5. READMEs canônicos de IDPW e Whats API

## Resultado da auditoria

### Documentos canônicos

| Arquivo | Papel |
|---|---|
| `docs/refoundation/GOAL.md` | visão e princípios |
| `docs/refoundation/CONTRACTS.md` | invariantes |
| `docs/architecture.md` | arquitetura global |
| `docs/refoundation/PLAN.md` | ordem de implementação |
| `TASKS.md` | backlog de execução |
| `INTEGRATION_GUIDE.md` | integração entre serviços |
| `IDC_Dominuslabs/README.md` | contrato do IDPW |
| `api_whatsapp_v1.2/README.md` | contrato do Resource Server |

### Documentos reescritos

| Arquivo | Problema identificado | Papel após saneamento |
|---|---|---|
| `README.md` | template Vite | índice do produto |
| `docs/architecture.md` | arquitetura M2M/eventos antiga | arquitetura canônica |
| `docs/frontend-omnichannel.md` | realtime local e fallback de sessão | arquitetura frontend target |
| `docs/wa-api.md` | duas especificações conflitantes | visão única da integração Dominus↔Whats API |
| `docs/n8n-workflows.md` | CURRENT/TARGET misturados | runtime + migração explicitamente separados |
| `docs/deployment.md` | runbook operacional público | guia genérico de deployment |
| `docs/media-pipeline.md` | contrato de mídia incompleto | CURRENT + target state machine |
| `api_whatsapp_v1.2/ARCHITECTURE.md` | proposta histórica | arquitetura do Resource Server |

### Documentos históricos

```text
BASELINE.md
FALLBACK_AUDIT.md
EVT_CATALOG.md
CHECKPOINT_ARCH.md
CHECKPOINT_DATA.md
CHECKPOINT_EVENTS.md
```

Eles preservam evidência de uma fase específica e não devem orientar arquitetura futura.

### Migration specs não canônicas

```text
N8N_ROUTER_SPEC.md
EVT_DEPRECATION.md
EVT_LEGACY_AUDIT.md
```

São úteis para execução/migração, mas não substituem GOAL/CONTRACTS/PLAN.

## Contradições que motivaram a reescrita

### M2M

Documentos antigos atribuíam à Whats API responsabilidade de assinatura/gestão de JWT. O contrato correto é:

```text
IDPW = M2M authority
Whats API = Resource Server
Dominus = business/control plane
Browser = sem autoridade M2M
```

### Session fallback

A lógica equivalente a:

```text
workingSession || availableSessions[0]
```

não é comportamento válido.

### Eventos

`message.status.updated` não pode se transformar em `message.created` e não pode disparar som/unread/browser notification de nova mensagem.

### Realtime

Realtime pertence à aplicação autenticada, não ao lifecycle do `OmnichannelView`.

### Mídia

Whats API é proprietária do lifecycle; frontend não depende de URL temporária do WhatsApp.

## Segurança documental

A auditoria detectou documentação com:

- endereços de infraestrutura;
- hostnames físicos;
- portas administrativas;
- nomes/IDs de containers;
- IDs de aplicação;
- IDs de workflow;
- comandos específicos de administração.

A política adotada é:

```text
public repository
→ contratos, arquitetura e placeholders

private operations inventory
→ topologia concreta, hosts, IDs e comandos administrativos
```

Este relatório deliberadamente não reproduz os valores removidos.

## Observação sobre CURRENT vs TARGET

Documentos canônicos podem descrever a arquitetura target, desde que deixem claro quando o código/runtime ainda está em migração.

Nunca declarar uma feature como deployed apenas porque existe em um branch.

## Resultado

A auditoria definiu a matriz usada pelo saneamento posterior. O relatório final e o estado atual estão em:

```text
docs/DOCUMENTATION_SANEAMENTO_REPORT.md
```
