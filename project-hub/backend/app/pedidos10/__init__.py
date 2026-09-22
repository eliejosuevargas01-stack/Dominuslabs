"""Pedidos10 Bridge module for DominusLabs backend."""
from app.pedidos10.bridge import Pedidos10Bridge
from app.pedidos10.manager import pedidos10_manager
from app.pedidos10.router import router as pedidos10_router
from app.pedidos10.schemas import PedidosEvent, CatalogItem, OrderItem

__all__ = [
    "Pedidos10Bridge",
    "pedidos10_manager",
    "pedidos10_router",
    "PedidosEvent",
    "CatalogItem",
    "OrderItem",
]
