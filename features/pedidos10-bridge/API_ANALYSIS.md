# 🔍 ANÁLISE DA API DO PEDIDOS10 GESTOR WEB

## Informações Capturadas em: 2026-09-22

---

## 📡 API BASE URL

```
https://api-monitor.pedidos10.com.br/api-gestor-V1/
```

---

## 🔐 SISTEMA DE AUTENTICAÇÃO

### Endpoint de Login
```
POST /auth
```

### Tokens Identificados
- `token-server`: Token do servidor (ex: `Ykdsae584sderopOuesOpaeo90`)
- `token-u`: Token único do usuário (ex: `0df6e3611c5af1cc64001055b3b05672`)

### Headers Necessários
```
Content-Type: application/json
```

### Body da Requisição (provável)
```json
{
  "login": "usuario",
  "senha": "senha",
  "id_origem": 12
}
```

---

## 📋 ENDPOINTS MAPEADOS

### 1. Autenticação
| Método | Endpoint | Status |
|--------|----------|--------|
| POST | `/auth` | ✅ Mapeado |

### 2. Usuário
| Método | Endpoint | Status |
|--------|----------|--------|
| GET | `/usuario/token-server/{token}/id-origem/{id}/num-versao/{v}/des-versao/{dv}/token-u/{tu}` | ✅ Mapeado |

### 3. Permissões
| Método | Endpoint | Status |
|--------|----------|--------|
| GET | `/permissoes/id_usuario/{id_user}/token-server/{token}/id-origem/{id}/...` | ✅ Mapeado |

### 4. Estabelecimento
| Método | Endpoint | Status |
|--------|----------|--------|
| GET | `/estabelecimento-abertura/id/{id}/...` | ✅ Status de abertura |
| GET | `/estabelecimento-cardapio/id_estabelecimento/{id}/...` | ✅ **CATÁLOGO** |
| PUT | `/estabelecimento-cardapio` | ✅ Atualizar catálogo |

### 5. Pedidos
| Método | Endpoint | Status |
|--------|----------|--------|
| GET | `/lista-pedidos-aguardando-confirmacao/array_id_estabelecimento/{id}/...` | ✅ Pedidos pendentes |
| GET | `/lista-pedidos/array_id_estabelecimento/{id}/...` | ✅ Todos os pedidos |

### 6. Dashboard
| Método | Endpoint | Status |
|--------|----------|--------|
| GET | `/dashboard/id_estabelecimento/{id}/periodo/hoje/...` | ✅ Dashboard do dia |
| GET | `/dashboard-vendas-semanais/...` | ✅ Vendas semanais |

### 7. Outros
| Método | Endpoint | Status |
|--------|----------|--------|
| GET | `/config-env/...` | ✅ Configurações de ambiente |
| GET | `/banners/id_estabelecimento/{id}/...` | ✅ Banners promocionais |
| GET | `/lista-faturas/id_estabelecimento/{id}/...` | ✅ Faturas |

---

## 📦 ESTRUTURA DO CATÁLOGO (PARCIAL)

```json
{
  "data": [
    {
      "id": "1020097",
      "des_item": "Nome do Produto",
      "des_complementar": "Descrição detalhada...",
      "...": "outros campos"
    }
  ]
}
```

---

## 🎯 PRÓXIMOS PASSOS

### Para implementar o Pedidos10 Bridge:

1. **Automação de Login**
   - Usar Playwright para login inicial
   - Capturar tokens da response
   - Persistir tokens em arquivo

2. **Replicação de Requisições**
   - Implementar cliente `httpx` com os tokens
   - Replicar chamadas da API

3. **Endpoints Prioritários**
   - `POST /auth` - Autenticação
   - `GET /lista-pedidos-aguardando-confirmacao` - Pedidos novos
   - `GET /lista-pedidos` - Histórico de pedidos
   - `GET /estabelecimento-cardapio` - Catálogo completo

4. **Integração com DominusLabs**
   - Mapper: Pedidos10 Order → DominusLabs OrderManagerOrder
   - WebSocket: Escutar novos pedidos em tempo real
   - Status sync: Atualizar status no Pedidos10

---

## 🔧 PARÂMETROS PADRÃO

```
id_origem: 12
num-versao: 1
des-versao: 2.0.25
```

---

## ⚠️ OBSERVAÇÕES

- Captcha: O site usa **reCAPTCHA Enterprise** (key: `6LedAForAAAAAI0daY8cca0nbm137ol7nPjQ0hYo`)
- Todos os endpoints GET requerem os tokens na URL
- Possível necessidade de headers específicos (User-Agent, Referer, etc.)

---

**Arquivo gerado automaticamente pelo script de captura Playwright**
