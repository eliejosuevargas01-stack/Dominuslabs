"""Cliente de catálogo (cardápio)."""
import logging
import time
from typing import List, Optional

import httpx

from app.pedidos10.constants import BASE_URL, TOKEN_SERVER, ID_ORIGEM, NUM_VERSAO, DES_VERSAO, CHROME_HEADERS
from app.pedidos10.schemas import Pedidos10Session, CatalogItem

logger = logging.getLogger("pedidos10.catalog_client")


class CatalogClient:
    """Cliente de catálogo Pedidos10."""

    def __init__(self):
        pass

    async def get_catalog(self, session: Pedidos10Session, merchant_id: str) -> List[CatalogItem]:
        """Busca catálogo de produtos do merchant."""
        qt_val = self._qt(session.token_u)
        url = f"{BASE_URL}/estabelecimento-cardapio/{qt_val}/token-server/{TOKEN_SERVER}/id-origem/{ID_ORIGEM}/num-versao/{NUM_VERSAO}/des-versao/{DES_VERSAO}/token-u/{session.token_u}"
        headers = {
            "authorization": session.jwt,
            "x-token": TOKEN_SERVER,
            **{k: v for k, v in CHROME_HEADERS.items() if k != "content-type"},
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            logger.error("Request error during get_catalog: %s", str(e))
            return []

        if response.status_code == 401:
            raise ValueError("Session expired")
        if not response.is_success:
            logger.error("get_catalog failed: %s", response.text)
            return []

        data = response.json()
        produtos = data.get("produtos", [])
        return [self._parse_item(p) for p in produtos]

    def _parse_item(self, raw: dict) -> CatalogItem:
        """Parse raw product dict para CatalogItem."""
        return CatalogItem(
            id_produto=raw.get("id_produto", ""),
            nome_produto=raw.get("nome_produto", ""),
            valor_produto=raw.get("valor_produto", ""),
            status_produto=raw.get("status_produto", ""),
            categoria=raw.get("categoria", ""),
            imagem_url=raw.get("imagem_url", ""),
        )

    @staticmethod
    def _qt(token_u: str) -> str:
        """Gera qt() = hash de token_u + timestamp."""
        ts = int(time.time() * 1000)
        raw = f"{token_u}:{ts}"
        import hashlib
        return hashlib.sha256(raw.encode()).hexdigest()
