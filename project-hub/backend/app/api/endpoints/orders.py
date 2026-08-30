"""Order Manager: entrada de pedidos, SSE e confirmação do operador."""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import decode_access_token
from app.core.config import settings
from app.core.database import get_db
from app.models.order_manager import OrderManagerOrder, OrderManagerOrderItem, utc_now
from sqlalchemy.orm import Session, joinedload

router = APIRouter()

orders: Dict[str, Dict[str, Any]] = {}
listeners: Dict[str, set[asyncio.Queue]] = {}
WEBHOOK_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
ORDER_STATUS_TRANSITIONS = {
    "pending": {"accepted"},
    "accepted": {"ready_for_delivery"},
    "ready_for_delivery": {"out_for_delivery"},
    "out_for_delivery": {"delivered"},
}


# --- N8N AI Agent Payload Schemas ---

class AgentOrderItem(BaseModel):
    codigo: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    quantidade: int = Field(gt=0)
    subtotal: Decimal = Field(ge=0)

class AgentOrderPayload(BaseModel):
    tenant_id: str = Field(min_length=1)
    pedido_id: str = Field(min_length=1)
    content_jid: str = Field(min_length=1)
    localização: Any
    items: List[AgentOrderItem]
    cliente_id: str = Field(min_length=1)

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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao notificar o aceite do pedido.",
        ) from exc


def aggregate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Consolida linhas repetidas do mesmo produto para o frontend."""
    aggregated: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = item["codigo"]
        if key not in aggregated:
            aggregated[key] = {**item}
        else:
            aggregated[key]["quantidade"] += item["quantidade"]
            aggregated[key]["subtotal"] += item["subtotal"]
    return list(aggregated.values())


def order_to_record(db_order: OrderManagerOrder) -> Dict[str, Any]:
    items = [
        {"codigo": item.codigo, "nome": item.nome, "quantidade": item.quantidade, "subtotal": float(item.subtotal)}
        for item in db_order.items
    ]
    return {
        "id": db_order.pedido_id,
        "tenant_id": db_order.tenant_id,
        "customer_name": db_order.cliente_id,
        "total": float(db_order.total),
        "address": db_order.address,
        "items": [{"name": item["nome"], "quantity": item["quantidade"], "codigo": item["codigo"]} for item in items],
        "status": db_order.status,
        "created_at": db_order.created_at.replace(tzinfo=timezone.utc).isoformat(),
        "content_jid": db_order.content_jid,
        "cliente_id": db_order.cliente_id,
        "items_source": items,
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
    payload: AgentOrderPayload,
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    """Recebe o pedido ESTRITO do agente IA (N8N) e publica no Order Manager."""
    if not valid_master_key(x_master_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")
        
    storage_id = f"{payload.tenant_id}:{payload.pedido_id}"
    existing = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter_by(
        tenant_id=payload.tenant_id, pedido_id=payload.pedido_id
    ).first()
    if existing:
        record = order_to_record(existing)
        orders[storage_id] = record
        return {"ok": True, "duplicate": True, "order": public_order(record)}

    canonical_items = aggregate_items([
        {
            "codigo": item.codigo,
            "nome": item.nome,
            "quantidade": item.quantidade,
            "subtotal": float(item.subtotal),
        }
        for item in payload.items
    ])

    total_calc = sum(item["subtotal"] for item in canonical_items)
            
    # Mapeando os itens
    frontend_items = [
        {"name": item["nome"], "quantity": item["quantidade"], "codigo": item["codigo"]}
        for item in canonical_items
    ]
    
    # Tratando a localização que a IA pode mandar como objeto ou string
    address_str = ""
    if isinstance(payload.localização, dict):
        address_str = payload.localização.get("endereco_completo", str(payload.localização))
    else:
        address_str = str(payload.localização)
        
    record = {
        "id": payload.pedido_id, 
        "tenant_id": payload.tenant_id,
        "customer_name": payload.cliente_id, 
        "total": total_calc, 
        "address": address_str,
        "items": frontend_items,
        "status": "pending", 
        "created_at": datetime.now(timezone.utc).isoformat(),
        "content_jid": payload.content_jid,
        "cliente_id": payload.cliente_id,
        "items_source": canonical_items,
    }
    
    db_order = OrderManagerOrder(
        tenant_id=payload.tenant_id, pedido_id=payload.pedido_id,
        cliente_id=payload.cliente_id, client_jid=payload.cliente_id, content_jid=payload.content_jid,
        address=address_str, total=total_calc, status="pending",
        items=[OrderManagerOrderItem(codigo=item["codigo"], nome=item["nome"], quantidade=item["quantidade"], subtotal=item["subtotal"]) for item in canonical_items],
    )
    db.add(db_order)
    db.commit()
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
            listeners.get(tenant_id, set()).discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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
    tenant_id = payload.get("tenant_id") if payload else None
    if not tenant_id:
        tenant_id = request.query_params.get("tenant_id")
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
    tenant_id = payload.get("tenant_id") if payload else request.query_params.get("tenant_id")
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
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = payload.get("tenant_id") if payload else None
    if not tenant_id:
        tenant_id = request.query_params.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for confirmation")
    db_order = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter_by(
        tenant_id=tenant_id, pedido_id=order_id
    ).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    order = order_to_record(db_order)
    orders[f"{tenant_id}:{order_id}"] = order
    if order["status"] != "pending":
        return {"ok": True, "duplicate": True, "order": public_order(order)}

    await notify_order_status(order_id, tenant_id, "order_accepted", db_order.client_jid or db_order.cliente_id)

    db_order.status = "accepted"
    db_order.accepted_at = utc_now()
    db.commit()
    order["status"] = db_order.status
    await broadcast("order_updated", order)
    return {"ok": True, "order": public_order(order)}


@router.post("/{order_id}/status")
async def update_order_status(
    order_id: str,
    order_status: str = Query(..., alias="status"),
    request: Request = None,
    token: Optional[str] = Query(None),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db),
):
    """Avança o pedido na operação da cozinha e notifica o workflow."""
    if not valid_operator(request, x_master_api_key or token):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = operator_payload(request, x_master_api_key or token)
    tenant_id = payload.get("tenant_id") if payload else request.query_params.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    allowed_statuses = {"ready_for_delivery", "out_for_delivery", "delivered"}
    if order_status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Invalid order status")
    db_order = db.query(OrderManagerOrder).options(joinedload(OrderManagerOrder.items)).filter_by(
        tenant_id=tenant_id, pedido_id=order_id
    ).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    if db_order.status == order_status:
        return {"ok": True, "duplicate": True, "order": public_order(order_to_record(db_order))}
    if order_status not in ORDER_STATUS_TRANSITIONS.get(db_order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order status from {db_order.status} to {order_status}",
        )

    await notify_order_status(order_id, tenant_id, order_status, db_order.client_jid or db_order.cliente_id)
    db_order.status = order_status
    db.commit()
    order = order_to_record(db_order)
    orders[f"{tenant_id}:{order_id}"] = order
    await broadcast("order_updated", order)
    return {"ok": True, "order": public_order(order)}

# --- TTS Logic ---
tts_cache: Dict[str, bytes] = {}

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
    tenant_id = payload.get("tenant_id") if payload else request.query_params.get("tenant_id")
    
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
        
    if order["id"] in tts_cache:
        def iterfile():
            yield tts_cache[order["id"]]
        return StreamingResponse(iterfile(), media_type="audio/mpeg")
        
    if not settings.LITELLM_API_KEY or not settings.LITELLM_API_BASE:
        raise HTTPException(status_code=500, detail="TTS not configured in backend")
        
    # Construir o texto
    items_text = ", ".join([f"{item['quantity']} {item['name']}" for item in order.get("items", [])])
    total_brl = f"R$ {order.get('total', 0):.2f}".replace(".", ",")
    text = f"Olá, o cliente {order.get('customer_name')} fez um novo pedido {items_text} no valor de {total_brl} para entregar em {order.get('address')}, por favor aceite."

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
            tts_cache[order["id"]] = audio_bytes
            
            def iterfile_new():
                yield audio_bytes
                
            return StreamingResponse(iterfile_new(), media_type="audio/mpeg")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")
