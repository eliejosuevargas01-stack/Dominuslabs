"""Orquestrador principal do Pedidos10 Bridge."""
import asyncio
import logging
from enum import Enum
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone

from app.pedidos10.auth_manager import AuthManager
from app.pedidos10.config_manager import ConfigManager
from app.pedidos10.mqtt_client import MqttClient
from app.pedidos10.event_dispatcher import EventDispatcher
from app.pedidos10.orders_client import OrdersClient
from app.pedidos10.catalog_client import CatalogClient
from app.pedidos10.schemas import (
    Pedidos10Session,
    MqttConfig,
    UsuarioResponse,
    PedidosEvent,
)

logger = logging.getLogger("pedidos10.bridge")


class BridgeStatus(Enum):
    """Status do bridge."""
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class Pedidos10Bridge:
    """
    Gerencia uma conexão Pedidos10 completa para um tenant/integration.

    Orquestra: AuthManager → ConfigManager → MqttClient → EventDispatcher
    """

    def __init__(
        self,
        tenant_id: str,
        integration_id: str,
        credentials_enc: str,
        on_order_callback: Optional[Callable[[PedidosEvent], None]] = None,
        on_message_callback: Optional[Callable[[PedidosEvent], None]] = None,
    ):
        self.tenant_id = tenant_id
        self.integration_id = integration_id
        self.credentials_enc = credentials_enc
        self.on_order_callback = on_order_callback
        self.on_message_callback = on_message_callback

        # Managers
        self.auth_manager = AuthManager()
        self.config_manager = ConfigManager()
        self.event_dispatcher = EventDispatcher(tenant_id)

        # Clients
        self.mqtt_client: Optional[MqttClient] = None
        self.orders_client = OrdersClient()
        self.catalog_client = CatalogClient()

        # State
        self._session: Optional[Pedidos10Session] = None
        self._mqtt_config: Optional[MqttConfig] = None
        self._status = BridgeStatus.STOPPED
        self._background_tasks: list = []
        self._start_time: Optional[datetime] = None
        self._channels: list = []
        self._last_event_at: Optional[datetime] = None

        # Register dispatcher callbacks
        if self.on_order_callback:
            self.event_dispatcher.register_callback("on_order", self._on_order_dispatch)
        if self.on_message_callback:
            self.event_dispatcher.register_callback("on_message", self._on_message_dispatch)

    async def start(self):
        """Inicia o bridge: auth → config → MQTT."""
        logger.info("Starting bridge for tenant %s, integration %s", self.tenant_id, self.integration_id)
        self._status = BridgeStatus.CONNECTING
        self._start_time = datetime.now(timezone.utc)

        try:
            # 1. Auth
            logger.info("Authenticating...")
            session = await self.auth_manager.get_session(self.credentials_enc)
            self._session = session

            # 2. Get user info para channels
            logger.info("Fetching user info...")
            user_info = await self.auth_manager.get_user_info(session)
            merchants = user_info.merchants
            channels = [m.get("des_channel_websocket") for m in merchants if m.get("des_channel_websocket")]

            if not channels:
                logger.warning("No websocket channels found in user info")

            # 3. Get MQTT config
            logger.info("Fetching MQTT config...")
            self._mqtt_config = await self.config_manager.get_mqtt_config(session)

            # 4. Initialize MQTT client
            logger.info("Initializing MQTT client...")
            self.mqtt_client = MqttClient(on_message=self._on_mqtt_message)

            if channels and self._mqtt_config and self._mqtt_config.mqtt_endpoint:
                # Store channels for property
                self._channels = channels
                # Connect to MQTT
                logger.info("Connecting to MQTT...")
                connected = await self.mqtt_client.connect(self._mqtt_config, channels)
                if not connected:
                    logger.error("Failed to connect to MQTT")
                    self._status = BridgeStatus.FAILED
                    return
                self._status = BridgeStatus.CONNECTED
                logger.info("Bridge connected successfully")
            else:
                logger.warning("No MQTT config available, using polling fallback only")
                self._status = BridgeStatus.CONNECTED

        except Exception as e:
            logger.error("Failed to start bridge: %s", str(e))
            self._status = BridgeStatus.FAILED
            raise

    async def stop(self):
        """Para o bridge gracefully."""
        logger.info("Stopping bridge for tenant %s", self.tenant_id)
        self._status = BridgeStatus.STOPPED

        if self.mqtt_client:
            await self.mqtt_client.disconnect()

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()

        self._session = None
        self._mqtt_config = None
        logger.info("Bridge stopped")

    async def restart(self):
        """Reinicia o bridge."""
        await self.stop()
        await asyncio.sleep(1)
        await self.start()

    def _on_mqtt_message(self, payload: dict):
        """Handle message MQTT_received via bridge."""
        asyncio.create_task(self.event_dispatcher.dispatch(payload))

    async def _on_order_dispatch(self, event: PedidosEvent):
        """Dispatch callback for order events."""
        self._last_event_at = datetime.now(timezone.utc)
        if self.on_order_callback:
            await self.on_order_callback(event)

    async def _on_message_dispatch(self, event: PedidosEvent):
        """Dispatch callback for message events."""
        self._last_event_at = datetime.now(timezone.utc)
        if self.on_message_callback:
            await self.on_message_callback(event)

    async def refresh(self):
        """Força novo login (reauth)."""
        logger.info("Refreshing session for tenant %s", self.tenant_id)
        try:
            session = await self.auth_manager.refresh(self.credentials_enc)
            self._session = session
            self.config_manager.invalidate_cache(session.token_u)
            mqtt_config = await self.config_manager.get_mqtt_config(session)
            self._mqtt_config = mqtt_config

            if self.mqtt_client:
                await self.mqtt_client.disconnect()
                await asyncio.sleep(1)
                if mqtt_config.mqtt_endpoint:
                    channels = []
                    if self._session:
                        user_info = await self.auth_manager.get_user_info(self._session)
                        channels = [m.get("des_channel_websocket") for m in user_info.merchants]
                    await self.mqtt_client.connect(mqtt_config, channels)

        except Exception as e:
            logger.error("Failed to refresh session: %s", str(e))
            raise

    @property
    def status(self) -> str:
        """Retorna status atual como string."""
        if self._status == BridgeStatus.CONNECTED and self.mqtt_client:
            mqtt_status = self.mqtt_client.status
            if mqtt_status == "RECONNECTING":
                return "RECONNECTING"
        return self._status.value

    @property
    def uptime(self) -> Optional[float]:
        """Retorna uptime em segundos."""
        if self._start_time:
            return (datetime.now(timezone.utc) - self._start_time).total_seconds()
        return None

    @property
    def channels(self) -> list:
        """Retorna lista de canais MQTT inscritos."""
        return self._channels

    async def _auto_reauth(self, method, *args, **kwargs):
        """Wrapper que captura ValueError de session expired e tenta refresh + retry."""
        try:
            return await method(*args, **kwargs)
        except ValueError as e:
            if "session expired" in str(e).lower():
                logger.info("Session expired detected, attempting auto-refresh...")
                await self.refresh()
                return await method(*args, **kwargs)
            raise

    async def get_pending_orders(self, merchant_id: str) -> list:
        """Busca pedidos pendentes (polling fallback)."""
        if not self._session:
            raise RuntimeError("Session not initialized")
        return await self._auto_reauth(self.orders_client.get_pending_orders, self._session, merchant_id)

    async def get_catalog(self, merchant_id: str) -> list:
        """Busca catálogo (polling fallback)."""
        if not self._session:
            raise RuntimeError("Session not initialized")
        return await self._auto_reauth(self.catalog_client.get_catalog, self._session, merchant_id)
