# 📐 Plano de Implementação do Backend (Implementation Plan)

## 1. Visão Geral
Este plano define as alterações técnicas no FastAPI para eliminar vulnerabilidades críticas (Path Traversal, vazamento SSE de chats e uploads desprotegidos), bem como sincronizar contratos do Order Manager e garantir estabilidade nas transações de banco de dados.

---

## 2. Especificação Técnica por Módulo

### 2.1 `app/api/endpoints/uploads.py`
- Em `get_uploaded_file(subfolder: str, filename: str)`:
  ```python
  base_dir = os.path.realpath(settings.UPLOAD_DIR)
  target_path = os.path.realpath(os.path.join(base_dir, subfolder, filename))
  if not target_path.startswith(base_dir + os.sep) and target_path != base_dir:
      raise HTTPException(status_code=403, detail="Acesso negado")
  if not os.path.exists(target_path) or not os.path.isfile(target_path):
      raise HTTPException(status_code=404, detail="Arquivo não encontrado")
  return FileResponse(target_path)
  ```

### 2.2 `app/api/endpoints/webhooks.py`
- No endpoint `/events/crm-chats`:
  - Validar token recebido (header ou query string) com `get_current_user_from_token`. Se inválido ou ausente, levantar `HTTPException(401, detail="Não autenticado")`.
  - Associar `listener_queue` a `(user.id, user.tenant_id)`.
- Na função `notify_crm_chat_listeners(message_data: dict, tenant_id: str)`:
  - Iterar sobre ouvintes e enviar a mensagem **somente** se o ouvinte pertencer ao mesmo `tenant_id`.

### 2.3 `app/api/endpoints/orders.py`
- Atualizar `ORDER_STATUS_TRANSITIONS`:
  ```python
  ORDER_STATUS_TRANSITIONS = {
      "pending": {"accepted", "rejected"},
      "accepted": {"preparing"},
      "preparing": {"ready"},
      "ready": {"out_for_delivery"},
      "out_for_delivery": {"delivered"},
      "delivered": set(),
      "rejected": set(),
      "cancelled": set(),
  }
  ```
- Implementar endpoint `POST /orders/{order_id}/reject`:
  ```python
  @router.post("/orders/{order_id}/reject")
  async def reject_order(order_id: str, request: Request, current_user = Depends(get_current_user)):
      # Validar transição, salvar status como "rejected" e notificar via websocket
  ```

### 2.4 `app/api/endpoints/product_media.py` e `main.py`
- Em `product_media.py`: Exigir `current_user: User = Depends(check_crm_permission)` em `upload_product_media`. Retornar URL consistente `/uploads/products/{filename}`.
- Em `main.py`: Montar `/uploads` apontando para `settings.UPLOAD_DIR`.

### 2.5 `app/api/endpoints/auth.py`
- Em `_maybe_provision`: Não receber `db: Session` da requisição HTTP. Instanciar `db = SessionLocal()` internamente com bloco `try/finally: db.close()`.
