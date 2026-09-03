"""Order Manager: entrada de pedidos, SSE e confirmação do operador."""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.core.auth import decode_access_token
from app.core.config import settings
from app.core.database import get_db
from app.models.order_manager import OrderManagerOrder, OrderManagerOrderItem, utc_now
from sqlalchemy.orm import Session, joinedload

router = APIRouter()

ORDER_CACHE_MAXSIZE = 10_000
ORDER_CACHE_TTL_SECONDS = 60 * 60
TTS_CACHE_MAX_BYTES = 32 * 1024 * 1024
TTS_CACHE_TTL_SECONDS = 10 * 60
WEBSOCKET_HEARTBEAT_SECONDS = 30

# These caches optimize reads only; PostgreSQL remains the source of truth.
orders: TTLCache = TTLCache(maxsize=ORDER_CACHE_MAXSIZE, ttl=ORDER_CACHE_TTL_SECONDS)
tts_cache: TTLCache = TTLCache(
    maxsize=TTS_CACHE_MAX_BYTES,
    ttl=TTS_CACHE_TTL_SECONDS,
    getsizeof=len,
)
listeners: Dict[str, set[asyncio.Queue]] = {}
websocket_listeners: Dict[str, set[WebSocket]] = {}
WEBHOOK_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
WEBHOOK_RETRY_DELAYS = (5, 15, 30, 60)
ORDER_STATUS_TRANSITIONS = {
    "pending": {"accepted", "rejected"},
    "accepted": {"preparing", "ready_for_delivery"},
    "preparing": {"ready", "ready_for_delivery"},
    "ready": {"out_for_delivery"},
    "ready_for_delivery": {"out_for_delivery"},
    "out_for_delivery": {"delivered"},
    "delivered": set(),
    "rejected": set(),
    "cancelled": set(),
}


# --- N8N AI Agent Payload Schemas ---

class AgentOrderItem(BaseModel):
    id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    pedido_id: str = Field(min_length=1)
    produto_id: str = Field(min_length=1)
    nome_produto: str = Field(min_length=1)
    quantidade: int = Field(gt=0)
    preco_unitario: Decimal = Field(ge=0)
    subtotal: Decimal = Field(ge=0)
    observacoes: Optional[str] = None
    created_at: datetime


class AgentDeliveryAddress(BaseModel):
    endereco_completo: str = Field(min_length=1)


class AgentOrder(BaseModel):
    id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    cliente_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    metodo_pagamento: str = Field(min_length=1)
    tipo_entrega: str = Field(min_length=1)
    endereco_entrega: AgentDeliveryAddress
    taxa_entrega: Decimal = Field(ge=0)
    subtotal: Decimal = Field(ge=0)
    valor_total: Decimal = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class AgentOrderPayload(BaseModel):
    pedido: AgentOrder
    itens: List[AgentOrderItem] = Field(min_length=1)

# ------------------------------------


def public_order(order: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": order["id"], 
        "customerName": order["customer_name"],
        "tenantId": order["tenant_id"],
        "total": order["total"], 
        "address": order["address"],
        "items": order["items"], 
        "status": order["status"],
        "createdAt": order["created_at"],
    }


async def notify_order_status(pedido_id: str, tenant_id: str, order_status: str, client_jid: str) -> None:
    """Notifica o workflow externo após uma mudança operacional de status."""
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
            response = await client.post(
                settings.ACCEPT_ORDER_WEBHOOK_URL,
                json={
                    "pedido_id": pedido_id,
                    "tenant_id": tenant_id,
                    "client_jid": client_jid,
                    "status": order_status,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise exc


async def retry_order_status_webhook(pedido_id: str, tenant_id: str, order_status: str, client_jid: str) -> None:
    for delay in (0, *WEBHOOK_RETRY_DELAYS):
        if delay:
            await asyncio.sleep(delay)
        try:
            await notify_order_status(pedido_id, tenant_id, order_status, client_jid)
            return
        except httpx.HTTPError:
            continue


def record_from_agent_payload(payload: AgentOrderPayload) -> Dict[str, Any]:
    """Converte o contrato do n8n no formato público do Order Manager."""
    canonical_items = [
        {
            "external_item_id": item.id,
            "tenant_id": item.tenant_id,
            "pedido_id": item.pedido_id,
            "codigo": item.produto_id,
            "nome": item.nome_produto,
            "quantidade": item.quantidade,
            "preco_unitario": item.preco_unitario,
            "subtotal": item.subtotal,
            "observacoes": item.observacoes,
            "created_at": to_utc_naive(item.created_at),
        }
        for item in payload.itens
    ]
    # Alguns fluxos do n8n criam primeiro o pedido com os totais zerados e
    # depois acrescentam os itens. Nunca podemos transformar esse snapshot em
    # um pedido gratuito no PDV: derive o subtotal a partir dos itens e some a
    # taxa de entrega quando o total informado ainda não é utilizável.
    derived_subtotal = sum(
        (
            item["subtotal"]
            if item["subtotal"] > Decimal("0")
            else item["preco_unitario"] * item["quantidade"]
        )
        for item in canonical_items
    )
    total = payload.pedido.valor_total
    if total <= Decimal("0") and derived_subtotal > Decimal("0"):
        total = derived_subtotal + payload.pedido.taxa_entrega

    return {
        "id": payload.pedido.id,
        "tenant_id": payload.pedido.tenant_id,
        # The exact n8n contract has no customer name. Keep the WhatsApp JID
        # only in internal fields and never present it as a display name.
        "customer_name": "Cliente",
        "total": total.quantize(Decimal("0.01")),
        "address": payload.pedido.endereco_entrega.endereco_completo,
        "items": [
            {
                "id": item["external_item_id"], "tenant_id": item["tenant_id"], "pedido_id": item["pedido_id"],
                "name": item["nome"], "quantity": item["quantidade"], "codigo": item["codigo"],
                "preco_unitario": item["preco_unitario"], "subtotal": item["subtotal"],
                "observacoes": item["observacoes"], "created_at": to_utc_iso(item["created_at"])
            }
            for item in canonical_items
        ],
        # O status recebido (ex.: "ativo") é do pedido no n8n. O fluxo da
        # operação começa localmente como pendente até o operador aceitá-lo.
        "status": "pending",
        "created_at": to_utc_iso(payload.pedido.created_at),
        "content_jid": payload.pedido.cliente_id,
        "cliente_id": payload.pedido.cliente_id,
        "items_source": canonical_items,
    }


def apply_order_snapshot(
    existing: OrderManagerOrder,
    record_data: Dict[str, Any],
) -> None:
    """Replace mutable order fields and line items with the latest n8n snapshot."""
    existing.total = record_data["total"]
    existing.address = record_data["address"]

    existing_items = {item.external_item_id: item for item in existing.items}
    incoming_ids = set()
    for item_data in record_data["items_source"]:
        external_item_id = item_data["external_item_id"]
        incoming_ids.add(external_item_id)
        persisted_item = existing_items.get(external_item_id)
        if persisted_item is None:
            existing.items.append(
                OrderManagerOrderItem(
                    external_item_id=external_item_id,
                    tenant_id=item_data["tenant_id"],
                    pedido_id=item_data["pedido_id"],
                    codigo=item_data["codigo"],
                    nome=item_data["nome"],
                    quantidade=item_data["quantidade"],
                    preco_unitario=item_data["preco_unitario"],
                    subtotal=item_data["subtotal"],
                    observacoes=item_data["observacoes"],
                    created_at=item_data["created_at"],
                )
            )
            continue

        persisted_item.codigo = item_data["codigo"]
        persisted_item.nome = item_data["nome"]
        persisted_item.quantidade = item_data["quantidade"]
        persisted_item.preco_unitario = item_data["preco_unitario"]
        persisted_item.subtotal = item_data["subtotal"]
        persisted_item.observacoes = item_data["observacoes"]

    # The envelope is a complete snapshot. Removing stale relationship members
    # activates delete-orphan and prevents cancelled items remaining in the PDV.
    for external_item_id, persisted_item in existing_items.items():
        if external_item_id not in incoming_ids:
            existing.items.remove(persisted_item)


def order_to_record(db_order: OrderManagerOrder) -> Dict[str, Any]:
    items = [
        {
            "external_item_id": item.external_item_id,
            "tenant_id": item.tenant_id,
            "pedido_id": item.pedido_id,
            "codigo": item.codigo, "nome": item.nome, "quantidade": item.quantidade,
            "preco_unitario": item.preco_unitario, "subtotal": item.subtotal,
            "observacoes": item.observacoes, "created_at": item.created_at
        }
        for item in db_order.items
    ]
    return {
        "id": db_order.pedido_id,
        "tenant_id": db_order.tenant_id,
        "customer_name": "Cliente",
        "total": db_order.total,
        "address": db_order.address,
        "items": [
            {
                "id": item["external_item_id"], "tenant_id": item["tenant_id"], "pedido_id": item["pedido_id"],
                "name": item["nome"], "quantity": item["quantidade"], "codigo": item["codigo"],
                "preco_unitario": item["preco_unitario"], "subtotal": item["subtotal"],
                "observacoes": item["observacoes"], "created_at": to_utc_iso(item["created_at"])
            }
            for item in items
        ],
        "status": db_order.status,
        "created_at": to_utc_iso(db_order.created_at),
        "content_jid": db_order.content_jid,
        "cliente_id": db_order.cliente_id,
        "items_source": items,
    }


def to_utc_naive(value: datetime) -> datetime:
    """Normalize external timestamps without depending on the server timezone."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def to_utc_iso(value: datetime) -> str:
    return to_utc_naive(value).replace(tzinfo=timezone.utc).isoformat()


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


def resolve_tenant_id(request: Request, payload: Optional[dict], credential: Optional[str]) -> Optional[str]:
    tenant_id = payload.get("tenant_id") if payload else None
    if tenant_id:
        return tenant_id
    master_credential = request.headers.get("X-Master-API-Key") or credential
    if valid_master_key(master_credential):
        return request.query_params.get("tenant_id")
    return None


async def broadcast(event: str, order: Dict[str, Any]) -> None:
    payload = jsonable_encoder({'event': event, 'order': public_order(order)})
    message = f"data: {json.dumps(payload)}\n\n"
    for queue in list(listeners.get(order["tenant_id"], set())):
        await queue.put(message)
    for websocket in list(websocket_listeners.get(order["tenant_id"], set())):
        try:
            await websocket.send_json(payload)
        except (RuntimeError, WebSocketDisconnect):
            tenant_sockets = websocket_listeners.get(order["tenant_id"])
            if tenant_sockets is not None:
                tenant_sockets.discard(websocket)
                if not tenant_sockets:
                    websocket_listeners.pop(order["tenant_id"], None)


@router.post("", status_code=status.HTTP_201_CREATED)
async def receive_order(
    payload: AgentOrderPayload,
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    """Recebe o pedido ESTRITO do agente IA (N8N) e publica no Order Manager."""
    if not valid_master_key(x_master_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")
        
    external_item_ids = set()
    for item in payload.itens:
        if item.tenant_id != payload.pedido.tenant_id or item.pedido_id != payload.pedido.id:
            raise HTTPException(status_code=400, detail="Scope inconsistency: item tenant_id or pedido_id does not match the parent order.")
        if item.id in external_item_ids:
            raise HTTPException(status_code=422, detail="Duplicate item id within the order payload.")
        external_item_ids.add(item.id)

    storage_id = f"{payload.pedido.tenant_id}:{payload.pedido.id}"
    record = record_from_agent_payload(payload)
    existing = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter_by(
        tenant_id=payload.pedido.tenant_id, pedido_id=payload.pedido.id
    ).first()
    if existing:
        apply_order_snapshot(existing, record)
        db.commit()
        db.refresh(existing)
        record = order_to_record(existing)
        orders[storage_id] = record
        await broadcast("order_updated", record)
        return {"ok": True, "duplicate": True, "order": public_order(record)}
    
    db_order = OrderManagerOrder(
        tenant_id=record["tenant_id"], pedido_id=record["id"],
        cliente_id=record["cliente_id"], client_jid=record["cliente_id"], content_jid=record["content_jid"],
        address=record["address"], total=record["total"], status=record["status"],
        created_at=to_utc_naive(payload.pedido.created_at),
        items=[
            OrderManagerOrderItem(
                external_item_id=item["external_item_id"],
                tenant_id=item["tenant_id"],
                pedido_id=item["pedido_id"],
                codigo=item["codigo"],
                nome=item["nome"],
                quantidade=item["quantidade"],
                preco_unitario=item["preco_unitario"],
                subtotal=item["subtotal"],
                observacoes=item["observacoes"],
                created_at=item["created_at"],
            ) for item in record["items_source"]
        ],
    )
    db.add(db_order)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent n8n retry may win after the initial duplicate lookup.
        # Re-read after rollback so the endpoint remains safely idempotent.
        db.rollback()
        existing = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter_by(
            tenant_id=payload.pedido.tenant_id, pedido_id=payload.pedido.id
        ).first()
        if existing:
            apply_order_snapshot(existing, record)
            db.commit()
            db.refresh(existing)
            record = order_to_record(existing)
            orders[storage_id] = record
            await broadcast("order_updated", record)
            return {"ok": True, "duplicate": True, "order": public_order(record)}
        raise
    db.refresh(db_order)
    record = order_to_record(db_order)
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
            while True:
                if await request.is_disconnected():
                    break
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            tenant_listeners = listeners.get(tenant_id)
            if tenant_listeners is not None:
                tenant_listeners.discard(queue)
                if not tenant_listeners:
                    listeners.pop(tenant_id, None)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.websocket("/ws")
async def order_websocket(websocket: WebSocket, token: Optional[str] = Query(None)):
    """Envia atualizações do Order Manager para todas as telas do mesmo tenant."""
    payload = decode_access_token(token) if token else None
    tenant_id = payload.get("tenant_id") if payload else None
    if not payload or not payload.get("sub") or not tenant_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    websocket_listeners.setdefault(tenant_id, set()).add(websocket)
    try:
        # The application heartbeat detects half-open mobile connections. The
        # client answers with a harmless pong; a failed ping reaches finally.
        while True:
            try:
                await asyncio.wait_for(websocket.receive(), timeout=WEBSOCKET_HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "ping"})
    except (RuntimeError, WebSocketDisconnect):
        pass
    finally:
        tenant_sockets = websocket_listeners.get(tenant_id)
        if tenant_sockets:
            tenant_sockets.discard(websocket)
            if not tenant_sockets:
                websocket_listeners.pop(tenant_id, None)


@router.get("")
async def list_orders(
    request: Request,
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    """Lista os pedidos que já foram oficialmente entregues ao Order Manager."""
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = resolve_tenant_id(request, payload, x_master_api_key or token)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    db_orders = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter(
        OrderManagerOrder.tenant_id == tenant_id
    ).order_by(OrderManagerOrder.created_at.desc()).all()
    records = [order_to_record(db_order) for db_order in db_orders]
    orders.update({f"{record['tenant_id']}:{record['id']}": record for record in records})
    return {"ok": True, "orders": [public_order(record) for record in records]}


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = resolve_tenant_id(request, payload, x_master_api_key or token)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    db_order = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter_by(
        tenant_id=tenant_id, pedido_id=order_id
    ).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    order = order_to_record(db_order)
    orders[f"{tenant_id}:{order_id}"] = order
    return {"ok": True, "order": public_order(order)}


@router.post("/{order_id}/accept")
async def accept_order(
    order_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = resolve_tenant_id(request, payload, x_master_api_key or token)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for confirmation")
    db_order = db.query(OrderManagerOrder).filter_by(
        tenant_id=tenant_id, pedido_id=order_id
    ).with_for_update().first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    order = order_to_record(db_order)
    if order["status"] != "pending":
        orders[f"{tenant_id}:{order_id}"] = order
        return {"ok": True, "duplicate": True, "order": public_order(order)}

    db_order.status = "accepted"
    db_order.accepted_at = utc_now()
    db.commit()
    order = order_to_record(db_order)
    orders[f"{tenant_id}:{order_id}"] = order
    await broadcast("order_updated", order)
    background_tasks.add_task(retry_order_status_webhook, order_id, tenant_id, "order_accepted", db_order.client_jid or db_order.cliente_id)
    return {"ok": True, "order": public_order(order)}


@router.post("/{order_id}/reject")
async def reject_order(
    order_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    """Rejeita o pedido e notifica ouvintes do websocket e webhook."""
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = resolve_tenant_id(request, payload, x_master_api_key or token)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for rejection")

    db_order = db.query(OrderManagerOrder).filter_by(
        tenant_id=tenant_id, pedido_id=order_id
    ).with_for_update().first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    order = order_to_record(db_order)
    if order["status"] == "rejected":
        orders[f"{tenant_id}:{order_id}"] = order
        return {"ok": True, "duplicate": True, "order": public_order(order)}

    if "rejected" not in ORDER_STATUS_TRANSITIONS.get(db_order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order status from {db_order.status} to rejected",
        )

    db_order.status = "rejected"
    db.commit()
    order = order_to_record(db_order)
    orders[f"{tenant_id}:{order_id}"] = order
    await broadcast("order_updated", order)
    background_tasks.add_task(retry_order_status_webhook, order_id, tenant_id, "order_rejected", db_order.client_jid or db_order.cliente_id)
    return {"ok": True, "order": public_order(order)}


@router.post("/{order_id}/status")
async def update_order_status(
    order_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    order_status: str = Query(..., alias="status"),
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    """Avança o pedido na operação da cozinha e notifica o workflow."""
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = resolve_tenant_id(request, payload, x_master_api_key or token)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    valid_statuses = set(ORDER_STATUS_TRANSITIONS.keys()) | {
        s for targets in ORDER_STATUS_TRANSITIONS.values() for s in targets
    }
    if order_status not in valid_statuses:
        raise HTTPException(status_code=422, detail="Invalid order status")
    db_order = db.query(OrderManagerOrder).filter_by(
        tenant_id=tenant_id, pedido_id=order_id
    ).with_for_update().first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    if db_order.status == order_status:
        return {"ok": True, "duplicate": True, "order": public_order(order_to_record(db_order))}
    if order_status not in ORDER_STATUS_TRANSITIONS.get(db_order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order status from {db_order.status} to {order_status}",
        )

    db_order.status = order_status
    db.commit()
    order = order_to_record(db_order)
    orders[f"{tenant_id}:{order_id}"] = order
    await broadcast("order_updated", order)
    background_tasks.add_task(retry_order_status_webhook, order_id, tenant_id, order_status, db_order.client_jid or db_order.cliente_id)
    return {"ok": True, "order": public_order(order)}

@router.get("/{order_id}/tts-alarm")
async def get_order_tts_alarm(
    order_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
        
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = resolve_tenant_id(request, payload, x_master_api_key or token)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    
    order = orders.get(f"{tenant_id}:{order_id}")
    if not order:
        db_order = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter_by(
            tenant_id=tenant_id, pedido_id=order_id
        ).first()
        order = order_to_record(db_order) if db_order else None
        if order:
            orders[f"{tenant_id}:{order_id}"] = order
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    cache_key = (tenant_id, order["id"])
    cached_audio = tts_cache.get(cache_key)
    if cached_audio is not None:
        return Response(content=cached_audio, media_type="audio/mpeg")
        
    if not settings.LITELLM_API_KEY or not settings.LITELLM_API_BASE:
        raise HTTPException(status_code=500, detail="TTS not configured in backend")
        
    # Construir o texto
    items_text = ", ".join([f"{item['quantity']} {item['name']}" for item in order.get("items", [])])
    total_brl = f"R$ {order.get('total', 0):.2f}".replace(".", ",")
    text = f"Olá, um novo pedido {items_text} no valor de {total_brl} para entregar em {order.get('address')}, por favor aceite."

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.LITELLM_API_BASE.rstrip('/')}/audio/speech",
                headers={"Authorization": f"Bearer {settings.LITELLM_API_KEY}"},
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "alloy"
                },
                timeout=30.0
            )
            resp.raise_for_status()
            audio_bytes = resp.content
            if len(audio_bytes) <= TTS_CACHE_MAX_BYTES:
                tts_cache[cache_key] = audio_bytes
            return Response(content=audio_bytes, media_type="audio/mpeg")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")
