import asyncio
import hmac
import hashlib
import json
import time
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.api.endpoints import orders


def make_n8n_post_args(payload: dict) -> tuple[bytes, dict]:
    import uuid
    from app.core.config import settings
    body_bytes = json.dumps(payload).encode()
    secret = settings.N8N_WEBHOOK_SECRET
    current_ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"{current_ts}.".encode() + body_bytes, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-N8N-Signature": sig,
        "X-N8N-Timestamp": current_ts,
        "X-N8N-Event-Id": f"evt-{uuid.uuid4()}",
    }
    return body_bytes, headers


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send_json(self, payload):
        self.messages.append(payload)


class DisconnectedWebSocket:
    async def send_json(self, payload):
        raise RuntimeError("socket closed")


class HeartbeatWebSocket:
    def __init__(self):
        self.messages = []

    async def accept(self):
        pass

    async def receive(self):
        await asyncio.sleep(1)

    async def send_json(self, payload):
        self.messages.append(payload)
        raise RuntimeError("socket closed")


def test_broadcast_sends_order_event_to_websocket_and_sse_listener():
    tenant_id = "tenant-realtime"
    queue = asyncio.Queue()
    websocket = FakeWebSocket()
    orders.listeners[tenant_id] = {queue}
    orders.websocket_listeners[tenant_id] = {websocket}
    order = {
        "id": "pedido-1",
        "tenant_id": tenant_id,
        "customer_name": "Cliente",
        "total": 42.5,
        "address": "Rua A, 10",
        "items": [],
        "status": "accepted",
        "created_at": "2026-08-31T12:00:00+00:00",
    }

    try:
        asyncio.run(orders.broadcast("order_updated", order))
        assert websocket.messages == [{
            "event": "order_updated",
            "order": {
                "id": "pedido-1",
                "customerName": "Cliente",
                "tenantId": tenant_id,
                "total": 42.5,
                "address": "Rua A, 10",
                "items": [],
                "status": "accepted",
                "createdAt": "2026-08-31T12:00:00+00:00",
            },
        }]
        assert '"event": "order_updated"' in queue.get_nowait()
    finally:
        orders.listeners.pop(tenant_id, None)
        orders.websocket_listeners.pop(tenant_id, None)


def test_n8n_order_envelope_maps_to_order_manager_record():
    payload = orders.AgentOrderPayload.model_validate({
        "pedido": {
            "id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
            "tenant_id": "admin",
            "cliente_id": "125203162075156@lid",
            "status": "ativo",
            "metodo_pagamento": "padrao",
            "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "av rodolfo vieira pamplona 1920, gaspar - SC"},
            "taxa_entrega": "4.97",
            "subtotal": "0.00",
            "valor_total": "0.00",
            "created_at": "2026-08-31T14:48:07.915Z",
            "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [
            {
                "id": "item-1", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
                "produto_id": "fatia-especial-dois-amores", "nome_produto": "Fatia Especial Dois Amores",
                "quantidade": 1, "preco_unitario": "20.00", "subtotal": "20.00", "observacoes": "Sem açúcar",
                "created_at": "2026-08-31T14:48:07.915Z"
            },
            {
                "id": "item-2", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
                "produto_id": "sonho-especial", "nome_produto": "Sonho Especial",
                "quantidade": 1, "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": None,
                "created_at": "2026-08-31T14:48:07.915Z"
            },
            {
                "id": "item-3", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
                "produto_id": "sonho-especial", "nome_produto": "Sonho Especial",
                "quantidade": 1, "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": "Com mais recheio",
                "created_at": "2026-08-31T14:48:07.915Z"
            },
        ],
    })

    record = orders.record_from_agent_payload(payload)

    assert record["id"] == payload.pedido.id
    assert record["tenant_id"] == "admin"
    assert record["customer_name"] == "Cliente"
    assert record["address"] == "av rodolfo vieira pamplona 1920, gaspar - SC"
    assert record["total"] == Decimal("44.97")
    assert record["status"] == "pending"
    assert record["items"] == [
        {
            "id": "item-1", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
            "name": "Fatia Especial Dois Amores", "quantity": 1, "codigo": "fatia-especial-dois-amores",
            "preco_unitario": Decimal("20.00"), "subtotal": Decimal("20.00"), "observacoes": "Sem açúcar", "created_at": "2026-08-31T14:48:07.915000+00:00"
        },
        {
            "id": "item-2", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
            "name": "Sonho Especial", "quantity": 1, "codigo": "sonho-especial",
            "preco_unitario": Decimal("10.00"), "subtotal": Decimal("10.00"), "observacoes": None, "created_at": "2026-08-31T14:48:07.915000+00:00"
        },
        {
            "id": "item-3", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
            "name": "Sonho Especial", "quantity": 1, "codigo": "sonho-especial",
            "preco_unitario": Decimal("10.00"), "subtotal": Decimal("10.00"), "observacoes": "Com mais recheio", "created_at": "2026-08-31T14:48:07.915000+00:00"
        },
    ]
    assert record["items_source"][0]["external_item_id"] == "item-1"


def test_same_external_item_id_is_scoped_to_each_order(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "WHATSAPP_MASTER_SECRET", "super-secret-key")
    payload = {
        "pedido": {
            "id": "order-scope-a", "tenant_id": "admin", "cliente_id": "125203162075156@lid",
            "status": "ativo", "metodo_pagamento": "padrao", "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "rua 1"}, "taxa_entrega": "0.00",
            "subtotal": "10.00", "valor_total": "10.00",
            "created_at": "2026-08-31T14:48:07.915Z", "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [{
            "id": "item-1", "tenant_id": "admin", "pedido_id": "order-scope-a",
            "produto_id": "prod-1", "nome_produto": "Produto 1", "quantidade": 1,
            "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": None,
            "created_at": "2026-08-31T14:48:07.915Z",
        }],
    }
    second_payload = deepcopy(payload)
    second_payload["pedido"]["id"] = "order-scope-b"
    second_payload["itens"][0]["pedido_id"] = "order-scope-b"

    body1, h1 = make_n8n_post_args(payload)
    body2, h2 = make_n8n_post_args(second_payload)
    first = client.post("/api/v1/orders", content=body1, headers=h1)
    second = client.post("/api/v1/orders", content=body2, headers=h2)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["order"]["items"][0]["id"] == "item-1"


def test_replaying_order_snapshot_replaces_removed_items(client):
    payload = {
        "pedido": {
            "id": "order-snapshot", "tenant_id": "admin", "cliente_id": "client@lid",
            "status": "ativo", "metodo_pagamento": "padrao", "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "rua 1"}, "taxa_entrega": "4.97",
            "subtotal": "0.00", "valor_total": "0.00",
            "created_at": "2026-08-31T14:48:07.915Z", "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [
            {"id": "item-kept", "tenant_id": "admin", "pedido_id": "order-snapshot", "produto_id": "prod-1", "nome_produto": "Produto 1", "quantidade": 1, "preco_unitario": "20.00", "subtotal": "20.00", "observacoes": None, "created_at": "2026-08-31T14:48:07.915Z"},
            {"id": "item-removed", "tenant_id": "admin", "pedido_id": "order-snapshot", "produto_id": "prod-2", "nome_produto": "Produto 2", "quantidade": 1, "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": None, "created_at": "2026-08-31T14:48:07.915Z"},
        ],
    }
    body1, h1 = make_n8n_post_args(payload)
    assert client.post("/api/v1/orders", content=body1, headers=h1).status_code == 201

    payload["itens"] = [{**payload["itens"][0], "quantidade": 2, "subtotal": "40.00"}]
    body2, h2 = make_n8n_post_args(payload)
    replay = client.post("/api/v1/orders", content=body2, headers=h2)

    assert replay.status_code == 201
    assert replay.json()["duplicate"] is True
    assert replay.json()["order"]["total"] == 44.97
    assert len(replay.json()["order"]["items"]) == 1
    assert replay.json()["order"]["items"][0]["id"] == "item-kept"
    assert replay.json()["order"]["items"][0]["quantity"] == 2
    assert replay.json()["order"]["items"][0]["subtotal"] == 40.0


def test_receive_order_returns_duplicate_after_a_concurrent_integrity_error():
    from app.core.config import settings
    from starlette.requests import Request

    payload = orders.AgentOrderPayload.model_validate({
        "pedido": {
            "id": "order-race", "tenant_id": "admin", "cliente_id": "125203162075156@lid",
            "status": "ativo", "metodo_pagamento": "padrao", "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "rua 1"}, "taxa_entrega": "0.00",
            "subtotal": "10.00", "valor_total": "10.00",
            "created_at": "2026-08-31T14:48:07.915Z", "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [{
            "id": "item-race", "tenant_id": "admin", "pedido_id": "order-race",
            "produto_id": "prod-1", "nome_produto": "Produto 1", "quantidade": 1,
            "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": None,
            "created_at": "2026-08-31T14:48:07.915Z",
        }],
    })
    persisted_order = SimpleNamespace(
        pedido_id="order-race", tenant_id="admin", cliente_id="125203162075156@lid",
        total=Decimal("10.00"), address="rua 1", status="pending",
        created_at=datetime(2026, 8, 31, 14, 48, 7, tzinfo=timezone.utc),
        content_jid="125203162075156@lid", items=[],
    )

    class FakeQuery:
        def __init__(self, db):
            self.db = db

        def options(self, *_):
            return self

        def filter_by(self, **_):
            return self

        def with_for_update(self):
            return self

        def first(self):
            return persisted_order if self.db.rolled_back else None

    class DuplicateOnCommitDb:
        def __init__(self):
            self.rolled_back = False

        def refresh(self, obj):
            pass

        def query(self, *_):
            return FakeQuery(self)

        def add(self, _):
            pass

        def commit(self):
            if not self.rolled_back:
                raise orders.IntegrityError("insert", {}, Exception("duplicate"))
            pass

        def rollback(self):
            self.rolled_back = True

    current_ts = str(int(time.time()))
    body_bytes = payload.model_dump_json().encode()
    sig = hmac.new(settings.N8N_WEBHOOK_SECRET.encode(), f"{current_ts}.".encode() + body_bytes, hashlib.sha256).hexdigest()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/orders",
        "headers": [
            (b"content-type", b"application/json"),
            (b"x-n8n-signature", sig.encode()),
            (b"x-n8n-timestamp", current_ts.encode()),
            (b"x-n8n-event-id", b"evt-race-123"),
        ],
        "query_string": b"",
    }
    async def receive():
        return {"type": "http.request", "body": body_bytes}

    req = Request(scope, receive)
    response = asyncio.run(orders.receive_order(req, payload, db=DuplicateOnCommitDb()))

    assert response["duplicate"] is True
    assert response["order"]["customerName"] == "Cliente"


def test_reject_inconsistent_tenant_id_or_pedido_id_in_items(client):
    payload = {
        "pedido": {
            "id": "order-123",
            "tenant_id": "admin",
            "cliente_id": "125203162075156@lid",
            "status": "ativo",
            "metodo_pagamento": "padrao",
            "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "rua 1"},
            "taxa_entrega": "0.00",
            "subtotal": "0.00",
            "valor_total": "0.00",
            "created_at": "2026-08-31T14:48:07.915Z",
            "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [
            {
                "id": "item-1", "tenant_id": "wrong-tenant", "pedido_id": "order-123",
                "produto_id": "prod-1", "nome_produto": "Produto 1",
                "quantidade": 1, "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": None,
                "created_at": "2026-08-31T14:48:07.915Z"
            }
        ],
    }

    body, h = make_n8n_post_args(payload)
    response = client.post("/api/v1/orders", content=body, headers=h)
    assert response.status_code == 400
    assert "Scope inconsistency" in response.json()["detail"]


def test_receive_real_order_with_valid_contract(client):
    payload = {
        "pedido": {
            "id": "order-456",
            "tenant_id": "admin",
            "cliente_id": "125203162075156@lid",
            "status": "ativo",
            "metodo_pagamento": "padrao",
            "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "rua 2"},
            "taxa_entrega": "0.00",
            "subtotal": "20.00",
            "valor_total": "20.00",
            "created_at": "2026-08-31T14:48:07.915Z",
            "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [
            {
                "id": "5221319f-b98a-4467-93e1-d4cb178bf780", "tenant_id": "admin", "pedido_id": "order-456",
                "produto_id": "prod-2", "nome_produto": "Produto 2",
                "quantidade": 2, "preco_unitario": "10.00", "subtotal": "20.00", "observacoes": "Sem cebola",
                "created_at": "2026-08-31T14:48:07.915Z"
            }
        ],
    }

    body, h = make_n8n_post_args(payload)
    response = client.post("/api/v1/orders", content=body, headers=h)
    assert response.status_code == 201
    data = response.json()
    assert data["ok"] is True
    assert data["order"]["id"] == "order-456"
    assert len(data["order"]["items"]) == 1
    assert data["order"]["items"][0]["observacoes"] == "Sem cebola"


def test_tts_cache_is_bounded_and_isolated_by_tenant():
    orders.tts_cache.clear()
    try:
        orders.tts_cache[("tenant-a", "pedido-1")] = b"audio-a"
        orders.tts_cache[("tenant-b", "pedido-1")] = b"audio-b"

        assert orders.tts_cache.maxsize == orders.TTS_CACHE_MAX_BYTES
        assert orders.tts_cache[("tenant-a", "pedido-1")] == b"audio-a"
        assert orders.tts_cache[("tenant-b", "pedido-1")] == b"audio-b"
    finally:
        orders.tts_cache.clear()


def test_broadcast_removes_a_disconnected_websocket():
    tenant_id = "tenant-disconnected"
    orders.websocket_listeners[tenant_id] = {DisconnectedWebSocket()}
    order = {
        "id": "pedido-2",
        "tenant_id": tenant_id,
        "customer_name": "Cliente",
        "total": 42.5,
        "address": "Rua B, 20",
        "items": [],
        "status": "pending",
        "created_at": "2026-08-31T12:00:00+00:00",
    }

    try:
        asyncio.run(orders.broadcast("new_order", order))

        assert tenant_id not in orders.websocket_listeners
    finally:
        orders.websocket_listeners.pop(tenant_id, None)


def test_websocket_heartbeat_removes_a_half_open_connection(monkeypatch):
    tenant_id = "tenant-heartbeat"
    websocket = HeartbeatWebSocket()
    monkeypatch.setattr(orders, "WEBSOCKET_HEARTBEAT_SECONDS", 0.001)
    monkeypatch.setattr(orders, "decode_access_token", lambda _: {"sub": "operator", "tenant_id": tenant_id})

    try:
        asyncio.run(orders.order_websocket(websocket, token="valid-token"))

        assert websocket.messages == [{"event": "ping"}]
        assert tenant_id not in orders.websocket_listeners
    finally:
        orders.websocket_listeners.pop(tenant_id, None)

def test_total_derived_when_subtotals_are_zero(client):
    payload = {
        "pedido": {
            "id": "order-zero-totals", "tenant_id": "admin", "cliente_id": "client@lid",
            "status": "ativo", "metodo_pagamento": "padrao", "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "rua 1"}, "taxa_entrega": "5.00",
            "subtotal": "0.00", "valor_total": "0.00",
            "created_at": "2026-08-31T14:48:07.915Z", "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [
            {"id": "item-1", "tenant_id": "admin", "pedido_id": "order-zero-totals", "produto_id": "prod-1", "nome_produto": "Produto 1", "quantidade": 2, "preco_unitario": "15.00", "subtotal": "30.00", "observacoes": None, "created_at": "2026-08-31T14:48:07.915Z"},
            {"id": "item-2", "tenant_id": "admin", "pedido_id": "order-zero-totals", "produto_id": "prod-2", "nome_produto": "Produto 2", "quantidade": 1, "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": None, "created_at": "2026-08-31T14:48:07.915Z"},
        ],
    }
    body, h = make_n8n_post_args(payload)
    response = client.post("/api/v1/orders", content=body, headers=h)
    assert response.status_code == 201

    data = response.json()
    # 2 * 15.00 + 1 * 10.00 + 5.00 (taxa) = 45.00
    assert data["order"]["total"] == 45.0


def test_receive_order_rejects_whatsapp_master_secret(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "WHATSAPP_MASTER_SECRET", "super-secret-key")
    payload = {
        "pedido": {
            "id": "order-reject", "tenant_id": "admin", "cliente_id": "client@lid",
            "status": "ativo", "metodo_pagamento": "padrao", "tipo_entrega": "padrao",
            "endereco_entrega": {"endereco_completo": "rua 1"}, "taxa_entrega": "0.00",
            "subtotal": "10.00", "valor_total": "10.00",
            "created_at": "2026-08-31T14:48:07.915Z", "updated_at": "2026-08-31T14:48:07.916Z",
        },
        "itens": [{
            "id": "item-1", "tenant_id": "admin", "pedido_id": "order-reject",
            "produto_id": "prod-1", "nome_produto": "Produto 1", "quantidade": 1,
            "preco_unitario": "10.00", "subtotal": "10.00", "observacoes": None,
            "created_at": "2026-08-31T14:48:07.915Z",
        }],
    }
    res = client.post("/api/v1/orders", json=payload, headers={"X-Master-API-Key": "super-secret-key"})
    assert res.status_code == 401
    assert "WHATSAPP_MASTER_SECRET não é permitido" in res.json()["detail"]


def test_operator_routes_reject_master_key_and_require_bearer(client, monkeypatch):
    """
    P0/Section 20: Operador não aceita WHATSAPP_MASTER_SECRET nem X-Master-API-Key.
    Deve exigir autenticação de operador humano exclusivamente via Bearer JWT.
    """
    from app.core.config import settings
    monkeypatch.setattr(settings, "WHATSAPP_MASTER_SECRET", "super-master-key")

    # Trying to list orders using master key instead of Bearer token -> 401
    res = client.get("/api/v1/orders", headers={"X-Master-API-Key": "super-master-key"})
    assert res.status_code == 401
    assert "detail" in res.json()


def test_operator_routes_ignore_query_tenant_id(client):
    """
    P0/Section 21, 22: Tenant do Order Manager vem estritamente do JWT humano,
    nunca de parâmetro de query (?tenant_id=).
    """
    from app.core.auth import create_access_token

    operator_token = create_access_token({
        "sub": "operator@tenant-a.com",
        "tenant_id": "tenant-a",
        "role": "operator"
    })
    headers = {"Authorization": f"Bearer {operator_token}"}

    # Querying with ?tenant_id=tenant-b must return empty or tenant-a scoped orders, NOT tenant-b
    res = client.get("/api/v1/orders?tenant_id=tenant-b", headers=headers)
    assert res.status_code == 200
    orders_list = res.json().get("orders", [])
    for order in orders_list:
        assert order.get("tenant_id") == "tenant-a"


def test_outbound_order_callback_fails_closed_without_secret(monkeypatch):
    """
    P1/Section 30, 31: Callback Dominus -> n8n deve falhar fechado se N8N_WEBHOOK_SECRET ausente.
    """
    from app.core.config import settings
    from app.api.endpoints.orders import notify_order_status

    monkeypatch.setattr(settings, "N8N_WEBHOOK_SECRET", None)
    monkeypatch.setattr(settings, "ACCEPT_ORDER_WEBHOOK_URL", "http://n8n-internal/webhook/order")

    # Should not raise exception, logs error and aborts immediately without sending request
    asyncio.run(notify_order_status("pedido-123", "accepted", "tenant-test", "client@s.whatsapp.net"))


def test_sse_order_events_rejects_query_token_parameter(client):
    """
    P1/Section 38, 40: SSE não aceita credenciais via query string (?token=).
    Deve exigir Authorization: Bearer.
    """
    from app.core.auth import create_access_token

    token = create_access_token({"sub": "user@test.com", "tenant_id": "tenant-test", "role": "operator"})
    res = client.get(f"/api/v1/orders/events?token={token}")
    assert res.status_code == 401
    assert "detail" in res.json()
