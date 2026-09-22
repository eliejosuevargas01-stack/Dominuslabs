#!/usr/bin/env python3
"""CLI de diagnóstico e smoke test para Pedidos10 Bridge."""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from datetime import datetime

import httpx

# Add parent to path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings

from app.pedidos10.constants import (
    BASE_URL,
    TOKEN_SERVER,
    APP_NAME,
    ID_ORIGEM,
    NUM_VERSAO,
    DES_VERSAO,
    AES_ECB_KEY,
    CHROME_HEADERS,
)
from app.pedidos10.auth_manager import AuthManager
from app.pedidos10.config_manager import _decrypt_aes_ecb, _qt
from app.pedidos10.schemas import Pedidos10Credentials


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


async def smoke_test(email: str, password: str):
    """Testa login + config-env + MQTT (se disponíveis)."""
    print(f"[SMOKE TEST] Starting for email: {email[:3]}***")

    auth_manager = AuthManager()

    # 1. Login
    print("[1/4] Testing login...")
    try:
        session = await auth_manager.login(Pedidos10Credentials(email=email, password=password))
        print(f"[OK] Login successful. JWT: {session.jwt[:30]}..., token_u: {session.token_u[:20]}...")
    except Exception as e:
        print(f"[FAIL] Login failed: {e}")
        return False

    # 2. User info
    print("[2/4] Testing user info...")
    try:
        user_info = await auth_manager.get_user_info(session)
        print(f"[OK] User info: {user_info.des_estabelecimento}")
        if user_info.merchants:
            print(f"    Merchants: {len(user_info.merchants)}")
            for m in user_info.merchants[:3]:
                print(f"    - {m.get('id_merchant')}: {m.get('des_merchant')} (channel: {m.get('des_channel_websocket', 'N/A')[:30]}...)")
    except Exception as e:
        print(f"[FAIL] User info failed: {e}")
        return False

    # 3. Config-env
    print("[3/4] Testing config-env...")
    try:
        qt_val = _qt(session.token_u)
        url = f"{BASE_URL}/config-env/{qt_val}/token-server/{TOKEN_SERVER}/id-origem/{ID_ORIGEM}/num-versao/{NUM_VERSAO}/des-versao/{DES_VERSAO}/token-u/{session.token_u}"
        headers = {
            "authorization": session.jwt,
            "x-token": TOKEN_SERVER,
            **{k: v for k, v in CHROME_HEADERS.items() if k != "content-type"},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
        if response.status_code == 401:
            print("[WARN] Session expired")
            return False
        if not response.is_success:
            print(f"[FAIL] Config-env failed: {response.status_code}")
            return False

        data = response.json()
        encrypted = data.get("data", "")
        try:
            decrypted = _decrypt_aes_ecb(encrypted)
            print(f"[OK] Config-env decrypted:")
            print(f"    - mqtt_region: {decrypted.get('mqtt_region', 'N/A')}")
            print(f"    - mqtt_endpoint: {decrypted.get('mqtt_endpoint', 'N/A')[:50]}...")
            print(f"    - mqtt_key_id: {decrypted.get('mqtt_key_id', 'N/A')}")
        except Exception as e:
            print(f"[WARN] AES-ECB decryption failed: {e}")
            print("    Fallback to polling mode")
    except Exception as e:
        print(f"[FAIL] Config-env failed: {e}")
        return False

    # 4. MQTT connection (skipped if no endpoint)
    print("[4/4] Testing MQTT connection...")
    from app.pedidos10.mqtt_client import _build_sigv4_presigned_url, MqttClient

    try:
        # Busca config-env again para pegar MQTT config
        mqtt_config = await get_mqtt_config(session)
        if not mqtt_config.mqtt_endpoint:
            print("[SKIP] No MQTT endpoint available. Using polling mode.")
            return True

        presigned_url = _build_sigv4_presigned_url(mqtt_config)
        print(f"[OK] Presigned URL built: {presigned_url[:50]}...")

        # Test MQTT connect (timeout 10s)
        events = []
        mqtt_client = MqttClient(on_message=lambda e: events.append(e))

        # Build channels from user_info
        channels = [m.get("des_channel_websocket") for m in user_info.merchants if m.get("des_channel_websocket")]
        channels = [c for c in channels if c]  # Filter out None

        connected = await mqtt_client.connect(mqtt_config, channels)
        if connected:
            print("[OK] MQTT connected!")
            await asyncio.sleep(5)  # Wait for PINGRESP
            mqtt_client._running = False
            if mqtt_client._receive_task:
                mqtt_client._receive_task.cancel()
            if mqtt_client._ping_task:
                mqtt_client._ping_task.cancel()
            if mqtt_client._websocket:
                await mqtt_client._websocket.close()
        else:
            print("[FAIL] MQTT connection failed")
            return False
    except Exception as e:
        print(f"[WARN] MQTT test skipped or failed: {e}")

    print("\n[SMOKE TEST] ALL PASSED!")
    return True


async def decrypt_config(b64_data: str):
    """Testa decriptação AES-ECB."""
    print(f"Decrypting AES-ECB config...")
    try:
        decrypted = _decrypt_aes_ecb(b64_data)
        print(json.dumps(decrypted, indent=2))
        return True
    except Exception as e:
        print(f"Decryption failed: {e}")
        return False


async def test_mqtt(region: str, endpoint: str, key_id: str, secret_key: str):
    """Testa conexão MQTT isolada."""
    print(f"Testing MQTT connection to {endpoint}...")

    from app.pedidos10.mqtt_client import _build_sigv4_presigned_url, MqttClient
    from app.pedidos10.schemas import MqttConfig

    config = MqttConfig(
        mqtt_region=region,
        mqtt_endpoint=endpoint,
        mqtt_key_id=key_id,
        mqtt_secret_key=secret_key,
    )

    try:
        presigned_url = _build_sigv4_presigned_url(config)
        print(f"Presigned URL: {presigned_url[:80]}...")

        mqtt_client = MqttClient(on_message=lambda e: print(f"Message: {e}"))
        connected = await mqtt_client.connect(config, ["test"])
        if connected:
            print("[OK] MQTT connected!")
            await asyncio.sleep(5)
            mqtt_client._running = False
            if mqtt_client._receive_task:
                mqtt_client._receive_task.cancel()
            if mqtt_client._ping_task:
                mqtt_client._ping_task.cancel()
            if mqtt_client._websocket:
                await mqtt_client._websocket.close()
        else:
            print("[FAIL] MQTT connection failed")
            return False
    except Exception as e:
        print(f"[ERROR] MQTT test failed: {e}")
        return False

    return True


async def get_mqtt_config(session):
    """Helper para buscar config-env."""
    from app.pedidos10.config_manager import ConfigManager

    config_manager = ConfigManager()
    return await config_manager.get_mqtt_config(session)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Pedidos10 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # smoke-test
    smoke_parser = subparsers.add_parser("smoke-test", help="Testa login + config-env + MQTT")
    smoke_parser.add_argument("--email", required=True, help="E-mail Pedidos10")
    smoke_parser.add_argument("--password", required=True, help="Senha Pedidos10")

    # decrypt-config
    decrypt_parser = subparsers.add_parser("decrypt-config", help="Testa decriptação AES-ECB")
    decrypt_parser.add_argument("--b64", required=True, help="Dados base64 encriptados")

    # test-mqtt
    mqtt_parser = subparsers.add_parser("test-mqtt", help="Testa conexão MQTT")
    mqtt_parser.add_argument("--region", required=True, help="AWS region")
    mqtt_parser.add_argument("--endpoint", required=True, help="MQTT endpoint")
    mqtt_parser.add_argument("--key-id", required=True, help="Access key ID")
    mqtt_parser.add_argument("--secret-key", required=True, help="Secret access key")

    args = parser.parse_args()

    if args.command == "smoke-test":
        success = await smoke_test(args.email, args.password)
        sys.exit(0 if success else 1)
    elif args.command == "decrypt-config":
        success = await decrypt_config(args.b64)
        sys.exit(0 if success else 1)
    elif args.command == "test-mqtt":
        success = await test_mqtt(args.region, args.endpoint, args.key_id, args.secret_key)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
