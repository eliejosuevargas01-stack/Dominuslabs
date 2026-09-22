"""Constantes da API Pedidos10 (API-Gestor-V1)."""
from typing import Final

# API Base
BASE_URL: Final[str] = "https://api-monitor.pedidos10.com.br/api-gestor-V1"

# Tokens e App (hardcoded no JS)
TOKEN_SERVER: Final[str] = "Ykdsae584sderopOuesOpaeo90"
APP_NAME: Final[str] = "Pedidos10-Gestor"
ID_ORIGEM: Final[str] = "12"
NUM_VERSAO: Final[int] = 1
DES_VERSAO: Final[str] = "2.0.25"

# Chave AES-ECB para decriptar config-env (tae do JS — Vr.enc.Utf8.parse(tae))
# YL era chave de localStorage, tae é a chave real do config-env
AES_ECB_KEY: Final[str] = "1d3fd3552357c0459537eaa5133ebe70"

# Headers de navegador (Chrome real)
CHROME_HEADERS: Final[dict] = {
    "authority": "api-monitor.pedidos10.com.br",
    "origin": "https://gestor-web.pedidos10.com.br",
    "referer": "https://gestor-web.pedidos10.com.br/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
}

# Tópicos MQTT (patterns)
MQTT_TOPIC_PATTERN: Final[str] = "pedidos10/{tenant_id}/{merchant_id}/#"
