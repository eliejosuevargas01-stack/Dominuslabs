import asyncio

from app.api.endpoints import orders


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
    assert record["customer_name"] == "125203162075156@lid"
    assert record["address"] == "av rodolfo vieira pamplona 1920, gaspar - SC"
    assert record["total"] == 0.0
    assert record["status"] == "pending"
    assert record["items"] == [
        {
            "id": "item-1", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
            "name": "Fatia Especial Dois Amores", "quantity": 1, "codigo": "fatia-especial-dois-amores",
            "preco_unitario": 20.0, "subtotal": 20.0, "observacoes": "Sem açúcar", "created_at": "2026-08-31T14:48:07.915000+00:00"
        },
        {
            "id": "item-2", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
            "name": "Sonho Especial", "quantity": 1, "codigo": "sonho-especial",
            "preco_unitario": 10.0, "subtotal": 10.0, "observacoes": None, "created_at": "2026-08-31T14:48:07.915000+00:00"
        },
        {
            "id": "item-3", "tenant_id": "admin", "pedido_id": "0848aa1a-8b98-49f7-ba32-9902c710c28e",
            "name": "Sonho Especial", "quantity": 1, "codigo": "sonho-especial",
            "preco_unitario": 10.0, "subtotal": 10.0, "observacoes": "Com mais recheio", "created_at": "2026-08-31T14:48:07.915000+00:00"
        },
    ]


def test_reject_inconsistent_tenant_id_or_pedido_id_in_items(client, monkeypatch):
    from app.core.config import settings
    import secrets

    monkeypatch.setattr(settings, "WHATSAPP_MASTER_SECRET", "super-secret-key")

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

    response = client.post("/api/v1/orders", json=payload, headers={"X-Master-API-Key": "super-secret-key"})
    assert response.status_code == 400
    assert "Scope inconsistency" in response.json()["detail"]


def test_receive_real_order_with_valid_contract(client, monkeypatch):
    from app.core.config import settings
    import secrets

    monkeypatch.setattr(settings, "WHATSAPP_MASTER_SECRET", "super-secret-key")

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

    response = client.post("/api/v1/orders", json=payload, headers={"X-Master-API-Key": "super-secret-key"})
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

    asyncio.run(orders.broadcast("new_order", order))

    assert tenant_id not in orders.websocket_listeners


def test_websocket_heartbeat_removes_a_half_open_connection(monkeypatch):
    tenant_id = "tenant-heartbeat"
    websocket = HeartbeatWebSocket()
    monkeypatch.setattr(orders, "WEBSOCKET_HEARTBEAT_SECONDS", 0.001)
    monkeypatch.setattr(orders, "decode_access_token", lambda _: {"sub": "operator", "tenant_id": tenant_id})

    asyncio.run(orders.order_websocket(websocket, token="valid-token"))

    assert websocket.messages == [{"event": "ping"}]
    assert tenant_id not in orders.websocket_listeners
