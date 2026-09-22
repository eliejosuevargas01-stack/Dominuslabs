"""Gerenciador global de bridges (singleton)."""
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime

from app.pedidos10.bridge import Pedidos10Bridge
from app.pedidos10.schemas import PedidosEvent

logger = logging.getLogger("pedidos10.manager")


class Pedidos10Manager:
    """
    Singleton global para gerenciar múltiplos bridges (um por integration ativa).

    Chave: integration.id (UUID)
    """

    def __init__(self):
        self._bridges: Dict[str, Pedidos10Bridge] = {}
        self._running = False
        self._on_order_callbacks: list = []
        self._on_message_callbacks: list = []

    async def start_integration(self, integration_id: str, db, tenant_id: str, credentials_enc: str):
        """
        Inicia bridge para uma integration.
        Cria Pedidos10Bridge e chama bridge.start().
        """
        from sqlalchemy.orm import Session
        from app.core.database import SessionLocal

        # Create callback closed over bridge
        async def on_order(event: PedidosEvent):
            await self._notify_on_order(tenant_id, event)

        async def on_message(event: PedidosEvent):
            await self._notify_on_message(tenant_id, event)

        bridge = Pedidos10Bridge(
            tenant_id=tenant_id,
            integration_id=integration_id,
            credentials_enc=credentials_enc,
            on_order_callback=on_order,
            on_message_callback=on_message,
        )

        await bridge.start()
        self._bridges[integration_id] = bridge
        logger.info("Bridge started for integration %s", integration_id)

    async def stop_integration(self, integration_id: str):
        """Para bridge e remove do dict."""
        if integration_id in self._bridges:
            bridge = self._bridges[integration_id]
            await bridge.stop()
            del self._bridges[integration_id]
            logger.info("Bridge stopped for integration %s", integration_id)

    async def restart_integration(self, integration_id: str, db, tenant_id: str, credentials_enc: str):
        """Stop + start."""
        await self.stop_integration(integration_id)
        await asyncio.sleep(1)
        await self.start_integration(integration_id, db, tenant_id, credentials_enc)

    def get_status(self, integration_id: str) -> Optional[dict]:
        """Retorna status de uma bridge específica."""
        if integration_id not in self._bridges:
            return None
        bridge = self._bridges[integration_id]
        return {
            "integration_id": integration_id,
            "tenant_id": bridge.tenant_id,
            "status": bridge.status,
            "uptime": bridge.uptime,
            "last_event_at": bridge._last_event_at.isoformat() if bridge._last_event_at else None,
        }

    def get_all_statuses(self) -> List[dict]:
        """Retorna status de todas as bridges ativas."""
        return [self.get_status(bridge_id) for bridge_id in self._bridges]

    async def _notify_on_order(self, tenant_id: str, event: PedidosEvent):
        """Notification handler for order events."""
        logger.info("Order event for tenant %s: %s", tenant_id, event.ind_evento)
        # Futuro: chamar n8n webhook, emit SSE, etc.

    async def _notify_on_message(self, tenant_id: str, event: PedidosEvent):
        """Notification handler for message events."""
        logger.info("Message event for tenant %s", tenant_id)
        # Futuro: processar mensagem do cliente

    async def start_all_active(self, db):
        """
        Inicia todas as integrations ativas do banco.
        A ser chamado no startup do FastAPI.
        """
        from app.models.tenant_platform_integration import TenantPlatformIntegration

        active = db.query(TenantPlatformIntegration).filter(
            TenantPlatformIntegration.platform == "pedidos10",
            TenantPlatformIntegration.is_active == True
        ).all()

        for integration in active:
            try:
                tenant_id = integration.tenant_id
                credentials_enc = integration.credentials_enc
                await self.start_integration(str(integration.id), db, tenant_id, credentials_enc)
            except Exception as e:
                logger.error("Failed to start integration %s: %s", integration.id, str(e))

    def is_running(self) -> bool:
        """Verifica se manager está rodando."""
        return self._running

    @property
    def bridge_count(self) -> int:
        """Retorna count de bridges ativas."""
        return len(self._bridges)


# Singleton
pedidos10_manager = Pedidos10Manager()
