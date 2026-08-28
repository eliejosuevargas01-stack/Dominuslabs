"""Order Manager: entrada de pedidos, SSE e confirmação do operador."""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, status, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import decode_access_token
from app.core.config import settings

router = APIRouter()


orders: Dict[str, Dict[str, Any]] = {}
listeners: Dict[str, set[asyncio.Queue]] = {}


def public_order(order: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": order["id"], "customerName": order["customer_name"],
        "tenantId": order["tenant_id"],
        "total": order["total"], "address": order["address"],
        "items": order["items"], "status": order["status"],
        "createdAt": order["created_at"],
    }


def valid_master_key(value: Optional[str]) -> bool:
    expected = settings.WHATSAPP_MASTER_SECRET
    return bool(expected and value and secrets.compare_digest(value.strip(), expected))


def operator_payload(request: Request, token: Optional[str]) -> Optional[dict]:
    if token and valid_master_key(token):
        return {"sub": "master", "tenant_id": None}
    auth = request.headers.get("authorization", "")
    candidate = auth[7:].strip() if auth.lower().startswith("bearer ") else token
    return decode_access_token(candidate) if candidate else None


def valid_operator(request: Request, token: Optional[str]) -> bool:
    payload = operator_payload(request, token)
    return bool(payload and payload.get("sub"))


async def broadcast(event: str, order: Dict[str, Any]) -> None:
    message = f"data: {json.dumps({'event': event, 'order': public_order(order)})}\n\n"
    for queue in list(listeners.get(order["tenant_id"], set())):
        await queue.put(message)


@router.post("", status_code=status.HTTP_201_CREATED)
async def receive_order(
    payload: Dict[str, Any] = Body(...),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
):
    """Recebe um pedido flexível do agente (N8N) e publica no Order Manager."""
    if not valid_master_key(x_master_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")
        
    tenant_id = payload.get("tenant_id") or payload.get("tenantId") or "admin"
    order_id = payload.get("pedido_id") or payload.get("order_id") or payload.get("id") or secrets.token_urlsafe(9)
    customer_name = payload.get("customer_name") or payload.get("customerName") or payload.get("customer_jid") or "Cliente WhatsApp"
    address = payload.get("address") or payload.get("loc") or "Endereço não informado"
    
    total = payload.get("total", 0.0)
    try:
        total = float(total)
    except:
        total = 0.0
        
    items = payload.get("items") or []
    if not items:
        payment = payload.get("payment_method", "Não especificado")
        items = [{"name": f"Pedido via IA (Pagamento: {payment})", "quantity": 1}]
        
    storage_id = f"{tenant_id}:{order_id}"
    record = {
        "id": order_id, "tenant_id": tenant_id,
        "customer_name": customer_name,
        "total": total, "address": address,
        "items": items,
        "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
    }
    orders[storage_id] = record
    await broadcast("new_order", record)
    return {"ok": True, "order": public_order(record)}


@router.get("/events")
async def order_events(request: Request, token: Optional[str] = Query(None)):
    payload = operator_payload(request, token)
    tenant_id = payload.get("tenant_id") if payload else None
    if not payload or not payload.get("sub") or not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    queue: asyncio.Queue = asyncio.Queue()
    listeners.setdefault(tenant_id, set()).add(queue)

    async def stream():
        try:
            yield ": connected\n\n"
            for order in list(orders.values()):
                if order["tenant_id"] == tenant_id and order["status"] == "pending":
                    yield f"data: {json.dumps({'event': 'new_order', 'order': public_order(order)})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            listeners.get(tenant_id, set()).discard(queue)

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
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = payload.get("tenant_id") if payload else None
    if not tenant_id:
        tenant_id = request.query_params.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for confirmation")
    order = orders.get(f"{tenant_id}:{order_id}")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order["status"] = "accepted"
    await broadcast("order_updated", order)
    return {"ok": True, "order": public_order(order)}
