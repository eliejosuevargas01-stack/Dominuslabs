"""
Identity Service (Dominus ⇄ Identity Client ⇄ Identity Worker)

Camada de compatibilidade que delega as operações ao IdentityClient centralizado.
"""
from typing import Optional
from app.services.identity_client import identity_client, IdentityClient


async def is_token_still_valid(token: str, margin_seconds: int = 30) -> bool:
    """
    Verifica se o token M2M/JWT é válido e tem mais de `margin_seconds` de vida útil restante.
    """
    return IdentityClient.is_token_still_valid(token, margin_seconds=margin_seconds)


async def get_m2m_jwt(tenant_id: str, scope: str = "whatsapp:sessions:read", aud: str = "whatsapp-api") -> str:
    """
    Obtém um JWT M2M estrito para o tenant_id e scope especificados via IdentityClient.
    """
    return await identity_client.get_token(tenant_id=tenant_id, scope=scope, aud=aud)


def invalidate_m2m_token(tenant_id: str, scope: Optional[str] = None, aud: str = "whatsapp-api") -> None:
    """
    Invalida o token em cache se for necessária renovação forçada.
    """
    identity_client.invalidate_token(tenant_id=tenant_id, scope=scope, aud=aud)
