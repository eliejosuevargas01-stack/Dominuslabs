"""Order Manager: entrada de pedidos, SSE e confirmação do operador."""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import decode_access_token
from app.core.config import settings

router = APIRouter()


class OrderItem(BaseModel):
    name: str
    quantity: int = Field(default=1, ge=1)


class OrderCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    customer_name: str = Field(alias="customerName")
    total: float = Field(ge=0)
    address: str
    items: List[OrderItem] = Field(default_factory=list)


orders: Dict[str, Dict[str, Any]] = {}
listeners: set[asyncio.Queue] = set()


def public_order(order: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": order["id"], "customerName": order["customer_name"],
        "total": order["total"], "address": order["address"],
        "items": order["items"], "status": order["status"],
        "createdAt": order["created_at"],
    }


def valid_master_key(value: Optional[str]) -> bool:
    expected = settings.WHATSAPP_MASTER_SECRET
    return bool(expected and value and secrets.compare_digest(value.strip(), expected))


def valid_operator(request: Request, token: Optional[str]) -> bool:
    if token and valid_master_key(token):
        return True
    auth = request.headers.get("authorization", "")
    candidate = auth[7:].strip() if auth.lower().startswith("bearer ") else token
    payload = decode_access_token(candidate) if candidate else None
    return bool(payload and payload.get("sub"))


async def broadcast(event: str, order: Dict[str, Any]) -> None:
    message = f"data: {json.dumps({'event': event, 'order': public_order(order)})}\n\n"
    for queue in list(listeners):
        await queue.put(message)


@router.post("", status_code=status.HTTP_201_CREATED)
async def receive_order(
    order: OrderCreate,
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
):
    """Recebe um pedido do agente e o publica para o Order Manager."""
    if not valid_master_key(x_master_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")
    order_id = order.id or secrets.token_urlsafe(9)
    record = {
        "id": order_id, "customer_name": order.customer_name,
        "total": order.total, "address": order.address,
        "items": [item.model_dump() for item in order.items],
        "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
    }
    orders[order_id] = record
    await broadcast("new_order", record)
    return {"ok": True, "order": public_order(record)}


@router.get("/events")
async def order_events(request: Request, token: Optional[str] = Query(None)):
    if not valid_operator(request, token):
        raise HTTPException(status_code=401, detail="Authentication required")
    queue: asyncio.Queue = asyncio.Queue()
    listeners.add(queue)

    async def stream():
        try:
            yield ": connected\n\n"
            for order in list(orders.values()):
                if order["status"] == "pending":
                    yield f"data: {json.dumps({'event': 'new_order', 'order': public_order(order)})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            listeners.discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{order_id}/accept")
async def accept_order(
    order_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
):
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order["status"] = "accepted"
    await broadcast("order_updated", order)
    return {"ok": True, "order": public_order(order)}
