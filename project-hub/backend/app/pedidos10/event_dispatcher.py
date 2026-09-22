"""Dispatcher de eventos MQTT Pedidos10."""
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

from app.pedidos10.schemas import PedidosEvent

logger = logging.getLogger("pedidos10.event_dispatcher")


class EventDispatcher:
    """Dispatch events recebidos do MQTT para callbacks registrados."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._callbacks: Dict[str, Callable] = {
            "on_order": None,
            "on_message": None,
            "on_store_close": None,
            "on_unknown": None,
        }

    def register_callback(self, event_type: str, callback: Callable[[PedidosEvent], None]):
        """Registra callback para tipo de evento."""
        if event_type in self._callbacks:
            self._callbacks[event_type] = callback
        else:
            raise ValueError(f"Unknown event type: {event_type}")

    async def dispatch(self, raw_message: dict):
        """Dispatch message recebida do MQTT."""
        try:
            event = self._parse_event(raw_message)
            await self._route_event(event)
        except Exception as e:
            logger.error("Error dispatching event: %s", str(e))

    def _parse_event(self, raw: dict) -> PedidosEvent:
        """Parse message bruta para PedidosEvent."""
        ind_evento = raw.get("ind_evento", "unknown")
        id_estabelecimento = raw.get("id_estabelecimento", "")

        return PedidosEvent(
            ind_evento=ind_evento,
            id_estabelecimento=id_estabelecimento,
            payload=raw,
            timestamp=datetime.now(timezone.utc),
        )

    async def _route_event(self, event: PedidosEvent):
        """Rota event para callback apropriado."""
        logger.info("Received event: %s for estabelecimento %s", event.ind_evento, event.id_estabelecimento)

        if event.ind_evento == "pedido":
            if self._callbacks["on_order"]:
                await self._callbacks["on_order"](event)
            else:
                logger.warning("on_order callback not registered")

        elif event.ind_evento == "mensagem":
            if self._callbacks["on_message"]:
                await self._callbacks["on_message"](event)
            else:
                logger.warning("on_message callback not registered")

        elif event.ind_evento == "fechamento-estabelecimento":
            if self._callbacks["on_store_close"]:
                await self._callbacks["on_store_close"](event)
            else:
                logger.warning("on_store_close callback not registered")

        elif event.ind_evento == "impressao":
            logger.debug("Print event received (ignored by bridge)")

        else:
            logger.warning("Unknown event type: %s", event.ind_evento)
            if self._callbacks["on_unknown"]:
                await self._callbacks["on_unknown"](event)

    def on_order(self, callback: Callable[[PedidosEvent], None]):
        """Decorator para registrar callback de ordem."""
        self.register_callback("on_order", callback)
        return callback

    def on_message(self, callback: Callable[[PedidosEvent], None]):
        """Decorator para registrar callback de mensagem."""
        self.register_callback("on_message", callback)
        return callback

    def on_store_close(self, callback: Callable[[PedidosEvent], None]):
        """Decorator para registrar callback de fechamento de estabelecimento."""
        self.register_callback("on_store_close", callback)
        return callback

    def on_unknown(self, callback: Callable[[PedidosEvent], None]):
        """Decorator para registrar callback de eventos desconhecidos."""
        self.register_callback("on_unknown", callback)
        return callback
