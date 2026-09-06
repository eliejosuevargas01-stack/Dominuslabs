"""
Módulo de autenticação exclusiva para integrações e webhooks do n8n.
Garante:
- Segredo independente (settings.N8N_WEBHOOK_SECRET)
- HMAC real (SHA256) sobre o corpo da requisição
- Validação de timestamp (rejeita requisições defasadas fora da janela de tolerância)
- Proteção contra replay com TTL cache de event_ids
- Rejeição estrita de tokens JWT de usuários humanos (inclusive administradores)
- Rejeição estrita de credenciais via query string
- Rejeição do uso de WHATSAPP_MASTER_SECRET
- Rejeição de segredo bruto como assinatura
"""
import hmac
import hashlib
import time
import secrets
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from cachetools import TTLCache

from app.core.config import settings
from app.core.auth import decode_access_token
from app.core.realtime_logger import log_realtime_event

# Cache para proteção contra replay de eventos (TTL = 300s = 5 minutos)
_n8n_seen_events: TTLCache = TTLCache(maxsize=10_000, ttl=300)


def authenticate_n8n_request(request: Request, raw_body_bytes: bytes) -> Dict[str, Any]:
    """
    Autentica requisições de serviço do n8n exclusivamente via HMAC.
    Rejeita JWTs humanos, segredos brutos, query params e WHATSAPP_MASTER_SECRET.
    """
    # 1. Rejeitar credenciais via query parameters
    forbidden_query_params = ["token", "api_key", "master_api_key", "x_master_api_key", "secret"]
    for qp in forbidden_query_params:
        if request.query_params.get(qp):
            log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
                "reason": f"Credenciais via query parameter '{qp}' não são permitidas",
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais via query string não são permitidas para webhooks n8n."
            )

    # 2. Rejeitar tokens de usuários humanos (inclusive admins)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token_str = auth_header[7:].strip()
        payload = decode_access_token(token_str)
        if payload and payload.get("sub"):
            log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
                "reason": "Token JWT de usuário humano rejeitado em webhook n8n",
                "sub": payload.get("sub"),
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: Webhooks n8n aceitam exclusivamente identidade de serviço, não tokens de usuários humanos."
            )

    # 3. Rejeitar X-Master-API-Key incondicionalmente
    master_key = request.headers.get("X-Master-API-Key") or request.headers.get("X-API-Key")
    if master_key:
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": "X-Master-API-Key não é permitida em rotas do n8n",
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Master-API-Key não é permitida em rotas do n8n."
        )

    # 4. Validar se o N8N_WEBHOOK_SECRET está configurado no servidor
    n8n_secret = getattr(settings, "N8N_WEBHOOK_SECRET", None)
    if not n8n_secret:
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": "N8N_WEBHOOK_SECRET não configurado no servidor",
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Serviço de webhook n8n não autenticado: segredo não configurado."
        )

    # 5. Obter cabeçalhos de assinatura obrigatórios
    signature = (
        request.headers.get("X-N8N-Signature")
        or request.headers.get("X-Signature")
        or request.headers.get("X-Dominus-Signature")
        or request.headers.get("X-Hub-Signature-256")
        or request.headers.get("X-Webhook-Secret")
    )
    if not signature:
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": "Assinatura ausente nos cabeçalhos",
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura HMAC ausente."
        )

    sig_clean = signature.replace("sha256=", "").strip()

    # Rejeitar explicitamente se a assinatura for o segredo bruto (raw secret)
    if secrets.compare_digest(sig_clean, n8n_secret.strip()):
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": "Segredo bruto enviado como assinatura",
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura inválida: segredo bruto não é permitido como assinatura HMAC."
        )

    # 6. Validar Timestamp obrigatório
    ts_header = (
        request.headers.get("X-N8N-Timestamp")
        or request.headers.get("X-Timestamp")
        or request.headers.get("X-Dominus-Timestamp")
    )
    if not ts_header:
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": "Timestamp ausente nos cabeçalhos",
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Timestamp ausente nos cabeçalhos."
        )

    tolerance = getattr(settings, "N8N_TIMESTAMP_TOLERANCE_SECONDS", 300)
    current_time = int(time.time())
    try:
        parsed_ts = int(ts_header)
        if abs(current_time - parsed_ts) > tolerance:
            log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
                "reason": "Timestamp do webhook expirado ou fora da tolerância",
                "timestamp": parsed_ts,
                "tolerance": tolerance,
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Requisição expirada: timestamp fora da janela de tolerância."
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de timestamp inválido."
        )

    # 7. Validar Event-ID obrigatório
    event_id = (
        request.headers.get("X-N8N-Event-Id")
        or request.headers.get("X-Event-Id")
        or request.headers.get("X-Dominus-Event-Id")
        or request.headers.get("X-Delivery-Id")
    )
    if not event_id:
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": "Event-ID ausente nos cabeçalhos",
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Event-ID ausente nos cabeçalhos."
        )

    # 8. Validar Assinatura HMAC ANTES de registrar no cache de replay (anti-poisoning)
    # Formato canônico estrito: HMAC(secret, timestamp + "." + event_id + "." + raw_body)
    # Vincula criptograficamente timestamp, event_id e corpo da requisição sem fallbacks.
    expected_sig = hmac.new(
        n8n_secret.encode(),
        f"{ts_header}.{event_id}.".encode() + raw_body_bytes,
        hashlib.sha256
    ).hexdigest()

    if not secrets.compare_digest(sig_clean, expected_sig):
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": "Assinatura HMAC inválida",
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura HMAC inválida."
        )

    # 9. Proteção contra Replay: validar se event_id já foi visto e registrar APENAS se HMAC foi aprovado
    if event_id in _n8n_seen_events:
        log_realtime_event("WEBHOOK_AUTH_FAILED", extra={
            "reason": f"Replay attack detectado para event_id: {event_id}",
            "event_id": event_id,
            "path": request.url.path
        })
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evento duplicado: requisição com este event_id já foi processada recentemente."
        )
    _n8n_seen_events[event_id] = current_time

    return {
        "type": "n8n_service",
        "is_admin": False,
        "event_id": event_id,
        "timestamp": parsed_ts
    }
