"""Pydantic schemas para o módulo Pedidos10."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, SecretStr


class Pedidos10Credentials(BaseModel):
    """Credenciais para login Pedidos10. Nunca serializar em log."""
    email: str = Field(..., description="E-mail do usuário")
    password: SecretStr = Field(..., description="Senha do usuário (nunca logar)")


class MqttConfig(BaseModel):
    """Configuração MQTT da AWS IoT Core."""
    mqtt_region: str
    mqtt_endpoint: str
    mqtt_key_id: str
    mqtt_secret_key: str


class Pedidos10Session(BaseModel):
    """Sessão autenticada: JWT + token-u."""
    jwt: str
    token_u: str
    estabelecimento_id: Optional[str] = None
    channel_websocket: Optional[str] = None
    merchant_id: Optional[str] = None


class CatalogItem(BaseModel):
    """Item do catálogo (cardápio)."""
    id_produto: str
    nome_produto: str
    valor_produto: str
    status_produto: str
    categoria: Optional[str] = None
    imagem_url: Optional[str] = None


class OrderItem(BaseModel):
    """Item de pedido."""
    id_pedido: str
    id_estabelecimento: str
    id_merchant: str
    status_pedido: str
    valor_total: str
    data_pedido: str
    itens: List[Dict[str, Any]] = Field(default_factory=list)
    cliente: Dict[str, Any] = Field(default_factory=dict)


class PedidosEvent(BaseModel):
    """Evento recebido via MQTT."""
    ind_evento: str  # "pedido", "mensagem", "fechamento-estabelecimento", "impressao"
    id_estabelecimento: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UsuarioResponse(BaseModel):
    """Resposta do endpoint /usuario."""
    id_estabelecimento: str
    des_estabelecimento: str
    merchants: List[Dict[str, Any]] = Field(default_factory=list)


class ConfigEnvResponse(BaseModel):
    """Resposta do endpoint /config-env (criptografada)."""
    data: str  # base64 + criptografado


class AuthResponse(BaseModel):
    """Resposta do endpoint /auth."""
    jwt: str
    des_token: str


class ErrorResponse(BaseModel):
    """Resposta de erro genérica."""
    error: str
    message: str
