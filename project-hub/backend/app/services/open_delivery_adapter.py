"""Open Delivery v1.7.x inbound adapter."""

from decimal import Decimal
from typing import Any, Dict, List


def convert_order_inbound(od_payload: Dict[str, Any], tenant_id: str, platform: str) -> Dict[str, Any]:
    """
    Convert Open Delivery payload to internal OrderManager format.

    Args:
        od_payload: The raw Open Delivery webhook payload (v1.7.x).
        tenant_id: The tenant identifier (from integration).
        platform: The platform identifier (e.g., 'open_delivery').

    Returns:
        A dictionary ready to be used as OrderManagerOrder and items.
    """
    # Extract order level fields
    order_info = od_payload.get('order', {})
    customer_info = order_info.get('customer', {})
    delivery_info = order_info.get('delivery', {})
    items_info = od_payload.get('items', [])

    external_order_id = str(order_info.get('id'))
    pedido_id = external_order_id  # as per mapping
    # client_id format: platform:merchant_id
    # merchant_id from order.merchant.id or top-level merchantId?
    merchant_id = order_info.get('merchant', {}).get('id') or od_payload.get('merchantId')
    cliente_id = f"{platform}:{merchant_id}" if merchant_id else f"{platform}:unknown"
    client_jid = None
    content_jid = None
    customer_name = customer_info.get('name', 'Cliente')
    # address: concatenate deliveryAddress fields
    address_parts = []
    if delivery_info:
        for field in ['street', 'number', 'complement', 'neighborhood', 'city', 'state', 'postalCode']:
            val = delivery_info.get(field)
            if val:
                address_parts.append(str(val))
    address = ', '.join(address_parts) if address_parts else ''
    # total
    total_raw = order_info.get('total', {}).get('orderAmount', 0)
    try:
        total = Decimal(str(total_raw))
    except Exception:
        total = Decimal('0')
    # status defaults to pending
    status = 'pending'
    source_platform = platform

    # Build items
    items = []
    for item in items_info:
        external_item_id = str(item.get('externalCode'))
        codigo = external_item_id  # as per mapping
        nome = item.get('name', '')
        quantidade = int(item.get('quantity', 0))
        preco_unitario_raw = item.get('unitPrice', 0)
        try:
            preco_unitario = Decimal(str(preco_unitario_raw))
        except Exception:
            preco_unitario = Decimal('0')
        subtotal_raw = item.get('totalPrice', 0)
        try:
            subtotal = Decimal(str(subtotal_raw))
        except Exception:
            subtotal = preco_unitario * quantidade
        observacoes = item.get('observations')
        items.append({
            'external_item_id': external_item_id,
            'tenant_id': tenant_id,
            'pedido_id': pedido_id,
            'codigo': codigo,
            'nome': nome,
            'quantidade': quantidade,
            'preco_unitario': preco_unitario,
            'subtotal': subtotal,
            'observacoes': observacoes,
        })

    return {
        'external_order_id': external_order_id,
        'source_platform': source_platform,
        'tenant_id': tenant_id,
        'pedido_id': pedido_id,
        'cliente_id': cliente_id,
        'client_jid': client_jid,
        'content_jid': content_jid,
        'customer_name': customer_name,
        'address': address,
        'total': total,
        'status': status,
        'items': items,
    }


# Mapping from internal status to Open Delivery endpoint (outbound)
STATUS_OUTBOUND_MAP = {
    'accepted': 'confirm',
    'preparing': 'preparing',
    'ready_for_delivery': 'readyForPickup',
    'out_for_delivery': 'dispatch',
    'delivered': 'delivered',
    'rejected': 'requestCancellation',
}