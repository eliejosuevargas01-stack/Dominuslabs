# Documento de Homologação Open Delivery

## Secão 1: Pré-requisitos

- Conta no sandbox Open Delivery (developer.opendelivery.com.br)
- Credenciais de homologação do Pedidos10 (solicitar via dev@dev10.com.br)
- DominusLabs rodando em HTTPS acessível publicamente
- URL base do DominusLabs configurada

## Secão 2: Configuração do ambiente de homologacao

### Variáveis de ambiente necessárias

```bash
# Para desenvolvimento local
DOMINUS_BASE_URL=http://localhost:8000
DOMINUS_TOKEN=seu_jwt_token_aqui
TEST_MERCHANT_ID=test_merchant_123

# Para homologação (ambiente real)
DOMINUS_BASE_URL=https://seusubdominio.dominuslabs.com
DOMINUS_TOKEN=token_jwt_do_operador
```

### Como cadastrar a integração via painel Integrações Delivery

1. Acesse o painel DominusLabs → Configurações → Integrações de Delivery
2. Clique em "Conectar" ao lado da plataforma desejada (Pedidos10, iFood, etc.)
3. No modal que aparece, insira o "Código da loja" fornecido pela plataforma
4. Clique em "Conectar" para finalizar o onboarding
5. A integração aparecerá na lista como "Ativa" com status de sincronização

### Como configurar o merchant_id correto

O merchant_id é automaticamente configurado durante o processo de conexão:
- O código da loja inserido pelo tenant torna-se o merchant_id no sistema
- Este ID é criptografado e armazenado na tabela `tenant_platform_integrations`
- Para validar, verifique o campo `merchant_id` na integração ativa via API:
  ```bash
  curl -H "Authorization: Bearer $DOMINUS_TOKEN" \
       $DOMINUS_BASE_URL/api/v1/integrations
  ```

## Secão 3: Checklist de homologacao (Open Delivery)

Checklist numerado com critérios testáveis:

1. [ ] Tenant conecta via painel sem ação técnica
2. [ ] GET /merchant retorna schema válido (validar com ferramenta opendelivery)
3. [ ] POST /orderUpdate processa pedido e aparece no Order Manager
4. [ ] Status 'aceito' no PDV → POST /orders/ID/confirm na plataforma
5. [ ] Status 'preparando' → POST /orders/ID/preparing
6. [ ] Status 'pronto para entrega' → POST /orders/ID/readyForPickup
7. [ ] Status 'em entrega' → POST /orders/ID/dispatch
8. [ ] Status 'entregue' → POST /orders/ID/delivered
9. [ ] Status 'rejeitado' → POST /orders/ID/requestCancellation
10. [ ] Webhook sem token válido retorna 401
11. [ ] Merchant_id desconhecido retorna 404
12. [ ] Pedido duplicado (mesmo ID) não duplica no Order Manager

## Secão 4: Scripts de teste

Comandos curl para testar cada endpoint localmente antes da homologacao real:

### Teste POST /orderUpdate com payload de exemplo

```bash
curl -X POST "$DOMINUS_BASE_URL/api/v1/od/pedidos10/orderUpdate" \
  -H "Authorization: Bearer fake-token-for-test" \
  -H "Content-Type: application/json" \
  -d '{
    "merchantId": "TEST_MERCHANT_123",
    "order": {
      "id": "OD-ORDER-001",
      "type": "DELIVERY",
      "customer": {
        "name": "João Silva"
      },
      "delivery": {
        "deliveryAddress": {
          "street": "Rua das Flores",
          "number": "123",
          "complement": "Apt 456",
          "neighborhood": "Centro",
          "city": "São Paulo",
          "state": "SP",
          "postalCode": "01234-567"
        }
      },
      "total": {
        "orderAmount": 45.90
      },
      "items": [
        {
          "externalCode": "BURGUER_CLASSICO",
          "name": "Hambúrguer Clássico",
          "quantity": 2,
          "unitPrice": 18.90,
          "totalPrice": 37.80,
          "observations": "Sem cebola"
        },
        {
          "externalCode": "COCA_COLA_LATA",
          "name": "Coca-Cola Lata 350ml",
          "quantity": 1,
          "unitPrice": 8.10,
          "totalPrice": 8.10
        }
      ]
    }
  }'
```

### Teste GET /merchant

```bash
curl -X GET "$DOMINUS_BASE_URL/api/v1/od/pedidos10/merchant" \
  -H "Authorization: Bearer fake-token-for-test" \
  -H "X-Merchant-Id: TEST_MERCHANT_123"
```

### Teste POST /acknowledgment

```bash
curl -X POST "$DOMINUS_BASE_URL/api/v1/od/pedidos10/events/acknowledgment" \
  -H "Authorization: Bearer fake-token-for-test" \
  -H "Content-Type: application/json" \
  -d '{
    "merchantId": "TEST_MERCHANT_123",
    "order": {
      "id": "OD-ORDER-001"
    }
  }'
```

### Payload de pedido Open Delivery v1.7.x de exemplo completo

```json
{
  "merchantId": "TEST_MERCHANT_123",
  "order": {
    "id": "OD-ORDER-001",
    "type": "DELIVERY",
    "customer": {
      "id": "CUST-001",
      "name": "Maria Oliveira",
      "email": "maria@email.com",
      "phone": "+55 11 99999-9999",
      "document": {
        "number": "12345678900",
        "type": "CPF"
      }
    },
    "delivery": {
      "deliveryAddress": {
        "street": "Av. Paulista",
        "number": "1000",
        "complement": "Conjunto 123",
        "neighborhood": "Bela Vista",
        "city": "São Paulo",
        "state": "SP",
        "postalCode": "01310-100",
        "reference": "Próximo ao MASP"
      },
      "estimatedDuration": 35,
      "deliveryWindow": {
        "start": "2026-09-21T19:30:00-03:00",
        "end": "2026-09-21T20:00:00-03:00"
      }
    },
    "total": {
      "orderAmount": 62.50,
      "currency": "BRL"
    },
    "items": [
      {
        "externalCode": "PICANHA_PRATA",
        "name": "Picanha na Chapa",
        "description": "Picanha grelhada ao ponto com farofa",
        "quantity": 1,
        "unitPrice": 42.90,
        "totalPrice": 42.90,
        "observations": "Ao ponto"
      },
      {
        "externalCode": "FEIJOADA_TRADICIONAL",
        "name": "Feijoada Tradicional",
        "description": "Feijoada completa com acompanhamentos",
        "quantity": 1,
        "unitPrice": 28.50,
        "totalPrice": 28.50
      },
      {
        "externalCode": "GUARANA_LATA",
        "name": "Guaraná Antarctica Lata 350ml",
        "quantity": 2,
        "unitPrice": 6.30,
        "totalPrice": 12.60
      }
    ],
    "payments": [
      {
        "type": "CREDIT_CARD",
        "amount": 62.50,
        "installments": 1,
        "status": "APPROVED",
        "tid": "123456789"
      }
    ],
    "status": "RECEIVED",
    "createdAt": "2026-09-21T18:45:00-03:00",
    "updatedAt": "2026-09-21T18:45:00-03:00"
  }
}
```

## Secão 5: Erros comuns e resolução

| Erro | Código HTTP | Causa | Solução |
|------|-------------|-------|---------|
| Missing or invalid Authorization header | 401 | Token ausente ou formato inválido | Verificar se header Authorization está presente como "Bearer <token>" |
| merchantId not found in payload | 400 | Campo merchantId ausente no body | Incluir merchantId no nível do pedido ou dentro de order.merchant.id |
| Integration not found for merchant_id and platform | 404 | Nenhuma integração ativa encontrada para o merchant_id + platform | Verificar se a integração está cadastrada e ativa via painel |
| Invalid or expired token | 401 | Token de autenticação da plataforma inválido/expirado | Renovar token via fluxo OAuth2 ou verificar credenciais armazenadas |
| Method not allowed | 405 | Endpoint acessado com método HTTP incorreto | Verificar documentação: orderUpdate e acknowledgment são POST, merchant é GET |
| Internal Server Error | 500 | Erro interno no processamento | Verificar logs do backend para detalhes específicos |

## Secão 6: Contato e próximos passos

### Como solicitar credenciais ao Pedidos10

Enviar email para dev@dev10.com.br com assunto:
```
[Homologação] DominusLabs - Integração Open Delivery
```
Incluir no corpo:
- Nome da sua empresa/Loja
- CNPJ da estabelecimento
- Contato técnico (nome, email, telefone)
- Ambiente desejado (sandbox ou homologação)
- Prazo esperado para conclusão

### Como registrar como Ordering Application no Open Delivery

1. Acessar developer.opendelivery.com.br
2. Fazer login com conta desenvolvedor
3. Navegar para "Minhas Aplicações" → "Criar Nova Aplicação"
4. Preencher:
   - Nome da aplicação: DominusLabs
   - Descrição: Plataforma de gestão para restaurantes
   - URL de redirecionamento: https://seusubdominio.dominuslabs.com/auth/callback
   - Escopos solicitados: orders.read, orders.write, merchant.read
5. Após criação, anotar o Client ID e Client Secret fornecidos
6. Configurar essas credenciais no DominusLabs via processo de conexão (código da loja ou OAuth)

### Como completar a homologação oficial

1. Executar todos os itens do Checklist de homologação (Seção 3)
2. Documentar evidências (prints, logs, vídeos) de cada teste exitoso
3. Enviar relatório completo para dev@dev10.com.br com assunto:
   ```
   [Relatório de Homologação] DominusLabs - Open Delivery v1.7.x
   ```
4. Aguardar validação da equipe técnica do Pedidos10 (até 5 dias úteis)
5. Após aprovação, solicitar migração para ambiente de produção
6. Comunicar aos tenants que a integração está disponível para uso

---
*Documento gerado para homologação com Pedidos10 - Open Delivery API v1.7.x*
*Versão: 1.0 | Data: 21/09/2026*