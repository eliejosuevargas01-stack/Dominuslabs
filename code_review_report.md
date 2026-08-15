# Relatório de Revisão de Código e Mapeamento de Bugs - Dominus Labs Backend

## 1. `project-hub/backend/app/api/endpoints/whatsapp.py`

*   **Bug**: Falta do cabeçalho `X-Master-API-Key` no provisionamento server-to-server.
*   **Severidade**: Crítica
*   **Descrição**: O provisionamento da API do WhatsApp não estava enviando o `X-Master-API-Key` em suas requisições, deixando a aplicação vulnerável.
*   **Refatoração**:
    ```python
    # Antes
    resp = await client.post(
        provision_url,
        json={"email": user.email, "tenant_id": tenant_id, "password": user.hashed_password},
    )

    # Depois
    headers = {"X-Master-API-Key": settings.WHATSAPP_MASTER_SECRET} if getattr(settings, "WHATSAPP_MASTER_SECRET", None) else {}
    resp = await client.post(
        provision_url,
        json={"email": user.email, "tenant_id": tenant_id, "password": user.hashed_password},
        headers=headers
    )
    ```

## 2. `project-hub/backend/app/api/endpoints/webhooks.py`

*   **Bug**: Falta de Validação de Assinatura (Webhook Signature/HMAC) no Inbound do WhatsApp e Instagram.
*   **Severidade**: Crítica
*   **Descrição**: O endpoint de webhooks recebia requisições diretas sem validar a sua autenticidade, abrindo brechas para a injeção de falsos webhooks (spoofing).
*   **Refatoração**:
    ```python
    # Antes
    @router.post("/inbound/whatsapp")
    async def whatsapp_inbound_webhook(request: Request):
        payload = await request.json()

    # Depois
    @router.post("/inbound/whatsapp")
    async def whatsapp_inbound_webhook(request: Request):
        signature = request.headers.get("X-Signature")
        if hasattr(settings, "WEBHOOK_SECRET") and settings.WEBHOOK_SECRET:
            import hmac
            import hashlib
            body = await request.body()
            expected_signature = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
            if not signature or not hmac.compare_digest(signature, expected_signature):
                return {"status": "ignored", "reason": "invalid signature"}

        payload = await request.json()
    ```

## 3. `project-hub/backend/app/api/endpoints/auth.py`

*   **Bug**: Falta do cabeçalho `X-Master-API-Key` na etapa de provisionamento assíncrono (background).
*   **Severidade**: Crítica
*   **Descrição**: O método `_provision_whatsapp_client` (acionado logo no login ou no refresh_token) também carecia de segurança na requisição para a WhatsApp API, ignorando a Master API Key.
*   **Refatoração**: Inclusão de `headers={"X-Master-API-Key": settings.WHATSAPP_MASTER_SECRET}` da mesma forma que na rota `whatsapp.py`.

*   **Bug**: Truncamento/Engolimento de Exceções em `_maybe_provision`
*   **Severidade**: Média
*   **Descrição**: A função `_maybe_provision` que é inserida como uma background task não possuía nenhum `try/except` abrangente. Em caso de falha de I/O de banco ou erro imprevisto, isso não seria logado.
*   **Refatoração**: Envolvimento da lógica em um bloco `try/except Exception` explícito para capturar, formatar o erro e emitir o log apropriado de maneira segura.
