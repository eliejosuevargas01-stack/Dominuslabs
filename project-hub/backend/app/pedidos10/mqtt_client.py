"""Cliente MQTT over WebSocket com SigV4 (AWS IoT Core)."""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed
from urllib.parse import quote
from app.pedidos10.schemas import MqttConfig

logger = logging.getLogger("pedidos10.mqtt_client")

MAX_RECONNECT_ATTEMPTS = 60




def _build_sigv4_presigned_url(config: MqttConfig) -> str:
    """
    Constrói SigV4 presigned URL para MQTT over WebSocket.
    Protocolo: AWS4-HMAC-SHA256.
    """
    region = config.mqtt_region
    endpoint = config.mqtt_endpoint
    access_key = config.mqtt_key_id
    secret_key = config.mqtt_secret_key

    if not all([region, endpoint, access_key, secret_key]):
        raise ValueError("MqttConfig incomplete. Cannot build SigV4 URL.")

    # 1. datetime
    datetime_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    date_str = datetime_str[:8]

    # 2. credential_scope
    credential_scope = f"{date_str}/{region}/iotdevicegateway/aws4_request"

    # 3. query params
    algorithm = "AWS4-HMAC-SHA256"
    credential = f"{access_key}/{credential_scope}"
    signed_headers = "host"
    x_amz_date = datetime_str

    query_params = (
        f"X-Amz-Algorithm={algorithm}"
        f"&X-Amz-Credential={quote(credential, safe="")}"
        f"&X-Amz-Date={x_amz_date}"
        f"&X-Amz-SignedHeaders={signed_headers}"
    )

    # 4. canonical_request
    canonical_uri = "/mqtt"
    canonical_querystring = query_params
    canonical_headers = f"host:{endpoint}\n"
    payload_hash = hashlib.sha256(b"").hexdigest()
    canonical_request = (
        f"GET\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    # 5. string_to_sign
    string_to_sign = (
        f"{algorithm}\n"
        f"{datetime_str}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )

    # 6. signing_key
    def sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    k_date = sign(f"AWS4{secret_key}".encode(), date_str)
    k_region = sign(k_date, region)
    k_service = sign(k_region, "iotdevicegateway")
    signing_key = sign(k_service, "aws4_request")

    # 7. signature
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    # 8. final URL
    presigned_url = f"wss://{endpoint}/mqtt?{query_params}&X-Amz-Signature={signature}"
    return presigned_url


class MqttClient:
    """Cliente MQTT over WebSocket com SigV4."""

    def __init__(self, on_message: Callable[[dict], None]):
        self.on_message = on_message
        self._config: Optional[MqttConfig] = None
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._running = False
        self._channels: list = []
        self._reconnect_delay = 3
        self._max_reconnect_delay = 60
        self._reconnect_attempts = 0

    async def connect(self, config: MqttConfig, channels: list[str]) -> bool:
        """Conecta ao MQTT usando SigV4 presigned URL."""
        if self._running:
            logger.warning("MQTT client already running")
            return True

        self._config = config
        self._channels = channels
        self._running = True
        self._reconnect_attempts = 0

        return await self._do_connect()

    async def _do_connect(self) -> bool:
        """Realiza conexão MQTT."""
        try:
            presigned_url = _build_sigv4_presigned_url(self._config)

            async with websockets.connect(
                presigned_url,
                subprotocols=["mqtt"],
                close_timeout=5,
                ping_interval=None,   # desabilita ping WS nativo — usamos MQTT PINGREQ
                ping_timeout=None,
            ) as ws:
                self._websocket = ws
                self._reconnect_delay = 3  # Reset delay on success
                self._reconnect_attempts = 0

                # Send CONNECT packet
                if not await self._send_connect():
                    logger.error("Failed to send CONNECT")
                    return False

                # Subscribe to channels
                for channel in self._channels:
                    if not await self._send_subscribe(channel):
                        logger.error(f"Failed to subscribe to {channel}")
                        return False

                logger.info("MQTT connected and subscribed to %d channels", len(self._channels))

                # Start receive loop
                self._receive_task = asyncio.create_task(self._receive_loop())
                self._ping_task = asyncio.create_task(self._ping_loop())

                # Wait for tasks
                await asyncio.gather(self._receive_task, self._ping_task)

        except ConnectionClosed as e:
            logger.warning("MQTT connection closed: %s", e)
            return await self._reconnect()
        except Exception as e:
            logger.error("MQTT connection error: %s", str(e))
            return await self._reconnect()

        return True

    async def _reconnect(self) -> bool:
        """Reconecta com backoff exponencial."""
        if not self._running:
            return False

        self._reconnect_attempts += 1
        
        if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error("Max reconnect attempts (%d) reached, failing", MAX_RECONNECT_ATTEMPTS)
            self._running = False
            return False
            
        delay = min(self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)), self._max_reconnect_delay)

        logger.info("Reconnecting to MQTT in %d seconds (attempt %d)", delay, self._reconnect_attempts)

        await asyncio.sleep(delay)

        # Check if still running
        if not self._running:
            return False

        return await self._do_connect()

    async def _send_connect(self) -> bool:
        """Envia MQTT CONNECT packet."""
        client_id = f"{int(time.time())}_{_random_alphanum(7)}"

        # Build CONNECT packet
        # Fixed header: 0x10 (CONNECT) + remaining length
        connect_flags = 0x02  # Clean session
        keepalive = 0x003C  # 60s

        client_id_bytes = client_id.encode("utf-8")
        payload = (
            # Protocol name
            b"\x00\x04" + b"MQTT" +
            # Level (3.1.1)
            b"\x04" +
            # Connect flags
            bytes([connect_flags]) +
            # Keepalive
            keepalive.to_bytes(2, "big") +
            # Client ID
            len(client_id_bytes).to_bytes(2, "big") + client_id_bytes
        )

        remaining_len = len(payload)
        fixed_header = bytes([0x10]) + _encode_remaining_length(remaining_len)

        try:
            await self._websocket.send(fixed_header + payload)
            # Espera CONNACK
            msg = await asyncio.wait_for(self._websocket.recv(), timeout=5)
            if msg[0] != 0x20:  # CONNACK
                logger.error("Unexpected response after CONNECT: %s", msg.hex())
                return False
            logger.info("MQTT CONNACK received")
            return True
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for CONNACK")
            return False
        except Exception as e:
            logger.error("Error sending CONNECT: %s", str(e))
            return False

    async def _send_subscribe(self, topic: str) -> bool:
        """Envia MQTT SUBSCRIBE packet."""
        packet_id = int(time.time()) & 0xFFFF

        topic_bytes = topic.encode("utf-8")
        payload = (
            packet_id.to_bytes(2, "big")
            + len(topic_bytes).to_bytes(2, "big")
            + topic_bytes
            + b"\x00"  # QoS 0
        )

        remaining_len = len(payload)
        fixed_header = bytes([0x82]) + _encode_remaining_length(remaining_len)

        try:
            await self._websocket.send(fixed_header + payload)
            logger.info("SUBSCRIBE sent for topic: %s", topic)
            return True
        except Exception as e:
            logger.error("Error sending SUBSCRIBE: %s", str(e))
            return False

    async def _receive_loop(self):
        """Loop principal de recebimento de mensagens MQTT."""
        try:
            while self._running:
                msg = await self._websocket.recv()
                await self._handle_message(msg)
        except ConnectionClosed:
            logger.info("WebSocket closed")
        except Exception as e:
            logger.error("Error in receive loop: %s", str(e))

    async def _handle_message(self, raw: bytes):
        """Parse e despacha mensagem MQTT."""
        if not raw:
            return

        fixed_header = raw[0]

        # PUBLISH (0x30)
        if (fixed_header & 0xF0) == 0x30:
            topic, payload = _parse_publish(raw)
            if topic and payload:
                try:
                    data = json.loads(payload.decode("utf-8"))
                    self.on_message(data)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in MQTT message: %s", payload)
        # PINGRESP (0xD0)
        elif fixed_header == 0xD0:
            logger.debug("PINGRESP received")
        else:
            logger.debug("Unhandled MQTT packet: %02X", fixed_header)

    async def _ping_loop(self):
        """Envia PINGREQ a cada 30s para keepalive."""
        while self._running:
            await asyncio.sleep(30)
            try:
                await self._websocket.send(b"\xC0\x00")  # PINGREQ
                logger.debug("PINGREQ sent")
            except Exception as e:
                logger.error("Error sending PINGREQ: %s", str(e))
                break

    async def disconnect(self):
        """Desconecta gracefully."""
        self._running = False
        logger.info("Disconnecting MQTT client...")

        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass

    @property
    def is_connected(self) -> bool:
        """Verifica se está conectado."""
        return self._running and self._websocket is not None and not getattr(self._websocket, 'closed', False) and not getattr(self._websocket, 'close_code', None)

    @property
    def status(self) -> str:
        """Retorna status atual."""
        if not self._running:
            return "STOPPED"
        ws = self._websocket
        is_closed = ws is None or getattr(ws, 'closed', False) or getattr(ws, 'close_code', None) is not None
        if is_closed:
            return "RECONNECTING" if self._reconnect_attempts > 0 else "CONNECTING"
        return "CONNECTED"


def _random_alphanum(length: int) -> str:
    """Gera string alfanumérica aleatória."""
    import random
    import string
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _encode_remaining_length(length: int) -> bytes:
    """Codifica remaining length em MQTT variável length."""
    encoded = bytearray()
    while True:
        byte = length % 128
        length = length // 128
        if length > 0:
            byte |= 0x80
        encoded.append(byte)
        if length == 0:
            break
    return bytes(encoded)


def _parse_publish(raw: bytes) -> tuple:
    """Parse MQTT PUBLISH packet."""
    # Fixed header
    fixed_header = raw[0]
    if (fixed_header & 0xF0) != 0x30:
        return None, None

    # Remaining length
    multiplier = 1
    value = 0
    idx = 1
    while True:
        encoded_byte = raw[idx]
        value += (encoded_byte & 0x7F) * multiplier
        multiplier *= 128
        idx += 1
        if (encoded_byte & 0x80) == 0:
            break

    # Topic length (2 bytes)
    if len(raw) < idx + 2:
        return None, None
    topic_len = int.from_bytes(raw[idx:idx + 2], "big")
    idx += 2

    # Topic
    if len(raw) < idx + topic_len:
        return None, None
    topic = raw[idx:idx + topic_len].decode("utf-8")
    idx += topic_len

    # Payload (resto do buffer)
    payload = raw[idx:]

    return topic, payload
