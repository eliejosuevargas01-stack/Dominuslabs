#!/usr/bin/env python3
"""
Script standalone para validar conexão MQTT Pedidos10 ao vivo.
Salva todos os eventos recebidos em events_log.csv
NÃO requer FastAPI rodando — roda direto.

Uso:
  cd /home/eliezer/Escritorio/dominuslabs/project-hub/backend
  PYTHONPATH=. .venv/bin/python app/pedidos10/test_live_mqtt.py
"""
import asyncio
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Adicionar o backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Logging verboso para ver tudo
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("pedidos10.live_test")

# Credenciais (pode sobrescrever via env vars)
EMAIL    = os.getenv("P10_EMAIL", "gostozinhos")
PASSWORD = os.getenv("P10_PASSWORD", "123456")

# Arquivo de saída
OUTPUT_CSV = Path(__file__).parent / "events_live.csv"

# ──────────────────────────────────────────────────────────────
# Imports do módulo (sem FastAPI, sem DB)
# ──────────────────────────────────────────────────────────────
from app.pedidos10.auth_manager import AuthManager
from app.pedidos10.config_manager import ConfigManager, _decrypt_aes_ecb
from app.pedidos10.mqtt_client import MqttClient, _build_sigv4_presigned_url
from app.pedidos10.schemas import Pedidos10Credentials, MqttConfig


# ──────────────────────────────────────────────────────────────
# CSV writer
# ──────────────────────────────────────────────────────────────
def init_csv(path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "ind_evento", "id_estabelecimento", "topic", "raw_payload"])
    logger.info(f"CSV inicializado: {path}")


def append_csv(path: Path, event: dict, topic: str, raw: str):
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            event.get("ind_evento", "unknown"),
            event.get("id_estabelecimento", ""),
            topic,
            raw[:2000],  # truncar payloads enormes
        ])


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
async def main():
    print("\n" + "="*60)
    print("  PEDIDOS10 MQTT LIVE TEST")
    print("="*60)
    print(f"Email: {EMAIL}")
    print(f"Output: {OUTPUT_CSV}\n")

    init_csv(OUTPUT_CSV)
    event_count = 0

    # ── PASSO 1: Login ──────────────────────────────────────────
    print("[1/4] Fazendo login no Pedidos10...")
    auth = AuthManager()
    creds = Pedidos10Credentials(email=EMAIL, password=PASSWORD)

    session = await auth.login(creds)
    print(f"      ✅ Login OK! JWT: {session.jwt[:40]}...")
    print(f"      token_u: {session.token_u}")

    # ── PASSO 2: Buscar dados do usuário (merchants + channels) ─
    print("\n[2/4] Buscando dados do usuário...")
    user_info = await auth.get_user_info(session)
    merchants = user_info.merchants
    print(f"      ✅ {len(merchants)} estabelecimento(s) encontrado(s):")
    channels = []
    for m in merchants:
        ch = m.get("des_channel_websocket", "")
        name = m.get("des_estabelecimento", "?")
        eid = m.get("id_estabelecimento", "?")
        print(f"         - [{eid}] {name}  →  channel: {ch}")
        if ch:
            channels.append(ch)
            # Atualizar session com o primeiro merchant encontrado
            if not session.estabelecimento_id:
                session.estabelecimento_id = str(eid)
                session.channel_websocket = ch
                session.merchant_id = str(eid)

    if not channels:
        print("      ⚠️  Nenhum canal WebSocket encontrado nos merchants!")
        print("      Verificar campo des_channel_websocket na resposta do /usuario")
        print("\nRaw user_info:")
        print(json.dumps(user_info, indent=2, ensure_ascii=False)[:2000])
        return

    # ── PASSO 3: Buscar config-env (credenciais MQTT) ───────────
    print("\n[3/4] Buscando config-env (credenciais AWS IoT MQTT)...")
    config_mgr = ConfigManager()
    mqtt_config = await config_mgr.get_mqtt_config(session)
    print(f"      ✅ MQTT Config recebida:")
    print(f"         Region:   {mqtt_config.mqtt_region}")
    print(f"         Endpoint: {mqtt_config.mqtt_endpoint}")
    print(f"         KeyId:    {mqtt_config.mqtt_key_id[:10]}...")

    # ── PASSO 4: Conectar ao MQTT e escutar ─────────────────────
    print(f"\n[4/4] Conectando ao AWS IoT Core MQTT...")
    print(f"      Endpoint: {mqtt_config.mqtt_endpoint}")
    print(f"      Canais: {channels}")
    print(f"\n      Salvando eventos em: {OUTPUT_CSV}")
    print("      Pressione Ctrl+C para parar.\n")
    print("-"*60)

    received = []

    def on_message(event: dict):
        nonlocal event_count
        event_count += 1
        ts = datetime.now(timezone.utc).isoformat()
        ind = event.get("ind_evento", "?")
        eid = event.get("id_estabelecimento", "?")
        raw = json.dumps(event, ensure_ascii=False)

        print(f"\n[{ts}] 📨 EVENTO #{event_count}")
        print(f"  ind_evento:          {ind}")
        print(f"  id_estabelecimento:  {eid}")
        print(f"  payload:             {raw[:300]}")

        append_csv(OUTPUT_CSV, event, channels[0] if channels else "", raw)
        received.append(event)

    client = MqttClient(on_message)

    try:
        connected = await client.connect(mqtt_config, channels)
        if not connected:
            print("❌ Falha ao conectar no MQTT. Verifique logs acima.")
            return

        print(f"✅ Conectado! Status: {client.status}")
        print("⏳ Aguardando eventos (max 5 minutos ou Ctrl+C)...\n")

        # Manter vivo por até 5 minutos
        start = time.time()
        while time.time() - start < 300:
            await asyncio.sleep(5)
            elapsed = int(time.time() - start)
            print(f"   [{elapsed}s] Status: {client.status} | Eventos recebidos: {event_count}", end="\r")
            if not client.is_connected:
                print(f"\n⚠️  Desconectado após {elapsed}s. Tentando reconectar...")
                break

    except KeyboardInterrupt:
        print(f"\n\n⌨️  Interrompido pelo usuário.")
    finally:
        await client.disconnect()
        print(f"\n{'='*60}")
        print(f"  RESUMO FINAL")
        print(f"{'='*60}")
        print(f"  Eventos recebidos: {event_count}")
        print(f"  Arquivo salvo:     {OUTPUT_CSV}")
        if event_count > 0:
            print(f"\n  Tipos de eventos:")
            from collections import Counter
            counts = Counter(e.get("ind_evento", "?") for e in received)
            for k, v in counts.items():
                print(f"    {k}: {v}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
