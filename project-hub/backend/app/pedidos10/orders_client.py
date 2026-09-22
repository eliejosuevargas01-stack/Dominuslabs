"""Cliente de pedidos (polling REST como fallback)."""
import logging
import time
from typing import List, Optional

import httpx

from app.pedidos10.constants import BASE_URL, TOKEN_SERVER, ID_ORIGEM, NUM_VERSAO, DES_VERSAO, CHROME_HEADERS
from app.pedidos10.schemas import Pedidos10Session, OrderItem

logger = logging.getLogger("pedidos10.orders_client")


class OrdersClient:
    """Cliente de pedidos usando polling REST (fallback quando MQTT falha)."""

    def __init__(self):
        pass

    async def get_pending_orders(self, session: Pedidos10Session, merchant_id: str) -> List[OrderItem]:
        """Busca pedidos aguardando confirmação."""
        qt_val = self._qt(session.token_u)
        url = f"{BASE_URL}/lista-pedidos-aguardando-confirmacao/{qt_val}/token-server/{TOKEN_SERVER}/id-origem/{ID_ORIGEM}/num-versao/{NUM_VERSAO}/des-versao/{DES_VERSAO}/token-u/{session.token_u}"
        headers = {
            "authorization": session.jwt,
            "x-token": TOKEN_SERVER,
            **{k: v for k, v in CHROME_HEADERS.items() if k != "content-type"},
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            logger.error("Request error during get_pending_orders: %s", str(e))
            return []

        if response.status_code == 401:
            raise ValueError("Session expired")
        if not response.is_success:
            logger.error("get_pending_orders failed: %s", response.text)
            return []

        data = response.json()
        pedidos = data.get("pedidos", [])
        return [self._parse_order(p) for p in pedidos]

    async def get_orders(self, session: Pedidos10Session, merchant_id: str) -> List[OrderItem]:
        """Busca todos os pedidos."""
        qt_val = self._qt(session.token_u)
        url = f"{BASE_URL}/lista-pedidos/{qt_val}/token-server/{TOKEN_SERVER}/id-origem/{ID_ORIGEM}/num-versao/{NUM_VERSAO}/des-versao/{DES_VERSAO}/token-u/{session.token_u}"
        headers = {
            "authorization": session.jwt,
            "x-token": TOKEN_SERVER,
            **{k: v for k, v in CHROME_HEADERS.items() if k != "content-type"},
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            logger.error("Request error during get_orders: %s", str(e))
            return []

        if response.status_code == 401:
            raise ValueError("Session expired")
        if not response.is_success:
            logger.error("get_orders failed: %s", response.text)
            return []

        data = response.json()
        pedidos = data.get("pedidos", [])
        return [self._parse_order(p) for p in pedidos]

    async def get_orders_since(self, session: Pedidos10Session, merchant_id: str, since: str) -> List[OrderItem]:
        """Busca pedidos desde timestamp (formato ISO 8601)."""
        # O Pedidos10 não suporta filtro por data diretamente
        # Faz todo polling e filtra no cliente
        all_orders = await self.get_orders(session, merchant_id)
        return [o for o in all_orders if o.data_pedido >= since]

    def _parse_order(self, raw: dict) -> OrderItem:
        """Parse raw order dict para OrderItem."""
        return OrderItem(
            id_pedido=raw.get("id_pedido", ""),
            id_estabelecimento=raw.get("id_estabelecimento", ""),
            id_merchant=raw.get("id_merchant", ""),
            status_pedido=raw.get("status_pedido", ""),
            valor_total=raw.get("valor_total", ""),
            data_pedido=raw.get("data_pedido", ""),
            itens=raw.get("itens", []),
            cliente=raw.get("cliente", {}),
        )

    @staticmethod
    def _qt(token_u: str) -> str:
        """Gera qt() = hash de token_u + timestamp."""
        ts = int(time.time() * 1000)
        raw = f"{token_u}:{ts}"
        import hashlib
        return hashlib.sha256(raw.encode()).hexdigest()
