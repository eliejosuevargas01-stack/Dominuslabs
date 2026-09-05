"""
Módulo de Logging Realtime Estruturado para o Dominuslabs.
Garante rastreabilidade de eventos SSE, Webhooks e Callbacks sem vazamento de segredos.
"""
import json
import logging
import os
import time
from typing import Optional, Any, Dict

logger = logging.getLogger("dominus.realtime")

_SENSITIVE_KEYS = {"password", "senha", "token", "secret", "access_token", "refresh_token", "jwt", "authorization", "private_key"}

def _sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for k, v in data.items():
        if k.lower() in _SENSITIVE_KEYS:
            cleaned[k] = "***REDACTED***"
        elif isinstance(v, dict):
            cleaned[k] = _sanitize_log_data(v)
        else:
            cleaned[k] = v
    return cleaned

def log_realtime_event(
    event_name: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    service: Optional[str] = None,
    session_id: Optional[str] = None,
    event_id: Optional[str] = None,
    pedido_id: Optional[str] = None,
    message_id: Optional[str] = None,
    listener_count: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    entry = {
        "event": event_name,
        "timestamp": time.time(),
        "process_id": os.getpid(),
    }
    if tenant_id: entry["tenant_id"] = tenant_id
    if user_id: entry["user_id"] = user_id
    if service: entry["service"] = service
    if session_id: entry["session_id"] = session_id
    if event_id: entry["event_id"] = event_id
    if pedido_id: entry["pedido_id"] = pedido_id
    if message_id: entry["message_id"] = message_id
    if listener_count is not None: entry["listener_count"] = listener_count
    if extra:
        entry.update(_sanitize_log_data(extra))

    logger.info(f"REALTIME | {event_name} | {json.dumps(entry)}")
