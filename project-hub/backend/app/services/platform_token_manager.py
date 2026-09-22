"""
Platform Token Manager

Obtém tokens OAuth2 client_credentials para plataformas externas (Pedidos10, iFood).
Segue o padrão do IdentityClient mas:
- Não usa criptografia de payload (Open Delivery e REST com Bearer)
- baseURL e auth_url vem do DB (TenantPlatformIntegration), não de env vars
- clientId/clientSecret vem do DB encriptado via decrypt_credentials()
- Endpoint OAuth2: POST CONCAT(auth_url, '/oauth/token') com grant_type=client_credentials
- Cache por chave (tenant_id, platform)
- Retry com backoff exponencial (3 tentativas)
- Fail-closed: sem credencial ou erro não-recuperável -> HTTPException 503
"""
import time
import logging
from typing import Optional, Dict, Any
from cachetools import TTLCache
from fastapi import HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.models.tenant_platform_integration import TenantPlatformIntegration
from app.core.credential_vault import decrypt_credentials
from app.core.http_client import get_async_client

logger = logging.getLogger("platform_token_manager")


class PlatformTokenManager:
    """
    Gerenciador único e centralizado para obtenção de tokens OAuth2 client_credentials
    para plataformas externas (Pedidos10, iFood, etc).
    """
    
    def __init__(self, cache_ttl: int = 3300, cache_maxsize: int = 512):
        """
        Inicializa o gerenciador de tokens com cache TTL.
        
        Args:
            cache_ttl: Tempo de vida do cache em segundos (padrão: 55 minutos)
            cache_maxsize: Tamanho máximo do cache
        """
        # Cache estritamente em memória: chave = (tenant_id, platform), valor = access_token
        self._cache: TTLCache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)

    async def get_token(self, tenant_id: str, platform: str, db: Session) -> str:
        """
        Obtém um token OAuth2 client_credentials para o tenant_id e plataforma especificados.
        
        Args:
            tenant_id: ID do tenant
            platform: Nome da plataforma (pedidos10, ifood, etc)
            db: Sessão do banco de dados
            
        Returns:
            str: token de acesso OAuth2
            
        Raises:
            HTTPException: 503 se não conseguir obter o token (fail-closed)
        """
        # Validações básicas de entrada
        if not isinstance(tenant_id, str) or not tenant_id.strip() or tenant_id != tenant_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id é obrigatório e deve ser uma string não vazada."
            )
        if not isinstance(platform, str) or not platform.strip() or platform != platform.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="platform é obrigatória e deve ser uma string não vazada."
            )

        cache_key = (tenant_id, platform)
        cached_token = self._cache.get(cache_key)
        if cached_token:
            logger.debug(f"[PLATFORM-TOKEN-MANAGER] Cache hit para tenant_id={tenant_id}, platform={platform}")
            return cached_token

        # Busca integração no banco de dados
        integration = db.query(TenantPlatformIntegration).filter(
            TenantPlatformIntegration.tenant_id == tenant_id,
            TenantPlatformIntegration.platform == platform,
            TenantPlatformIntegration.is_active == True
        ).first()

        if not integration:
            logger.error(f"[PLATFORM-TOKEN-MANAGER] Integração não encontrada para tenant_id={tenant_id}, platform={platform}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Integração com {platform} não configurada para o tenant {tenant_id}."
            )

        if not integration.auth_url:
            logger.error(f"[PLATFORM-TOKEN-MANAGER] auth_url não configurado para tenant_id={tenant_id}, platform={platform}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"URL de autenticação não configurada para a integração {platform}."
            )

        try:
            credentials = decrypt_credentials(integration.credentials_enc)
        except Exception as decrypt_err:
            logger.error(f"[PLATFORM-TOKEN-MANAGER] Falha ao decriptar credenciais para tenant_id={tenant_id}, platform={platform}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha ao processar credenciais da integração."
            )

        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        
        if not client_id or not client_secret:
            logger.error(f"[PLATFORM-TOKEN-MANAGER] Credenciais incompletas para tenant_id={tenant_id}, platform={platform}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Credenciais da integração incompletas."
            )

        # Construir URL do endpoint OAuth2
        base_auth_url = integration.auth_url.rstrip("/")
        token_url = f"{base_auth_url}/oauth/token"
        
        # Preparar requisição OAuth2 client_credentials
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        logger.info(f"[PLATFORM-TOKEN-MANAGER] Solicitando token OAuth2 para tenant_id={tenant_id}, platform={platform}")
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with get_async_client(timeout=15.0) as client:
                    resp = await client.post(token_url, data=payload, headers=headers)
                
                # Tratar diferentes códigos de status
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        access_token = data.get("access_token")
                        
                        if not access_token or not isinstance(access_token, str) or not access_token.strip():
                            logger.error(f"[PLATFORM-TOKEN-MANAGER] Resposta inválida do endpoint OAuth2 para tenant_id={tenant_id}, platform={platform}")
                            raise HTTPException(
                                status_code=status.HTTP_502_BAD_GATEWAY,
                                detail=f"Resposta inválida recebida do endpoint OAuth2 da plataforma {platform}."
                            )
                            
                        # Armazenar em cache
                        self._cache[cache_key] = access_token
                        logger.info(f"[PLATFORM-TOKEN-MANAGER] ✅ Token OAuth2 obtido com sucesso para tenant_id={tenant_id}, platform={platform}")
                        return access_token
                        
                    except ValueError as json_err:
                        logger.error(f"[PLATFORM-TOKEN-MANAGER] Resposta não-JSON do endpoint OAuth2 para tenant_id={tenant_id}, platform={platform}: {resp.text[:200]}")
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Resposta inválida recebida do endpoint OAuth2 da plataforma {platform}."
                        )
                        
                elif resp.status_code in (401, 403):
                    # Não tentar novamente em caso de credenciais inválidas
                    logger.error(f"[PLATFORM-TOKEN-MANAGER] Acesso negado pela plataforma {platform} (status {resp.status_code}) para tenant_id={tenant_id}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Credenciais inválidas para a plataforma {platform}. Verifique a configuração."
                    )
                    
                elif resp.status_code in (502, 503, 504, 408, 429) and attempt < max_retries - 1:
                    # Tentar novamente em caso de erros temporários
                    logger.warning(f"[PLATFORM-TOKEN-MANAGER] Plataforma {platform} retornou {resp.status_code}. Tentativa {attempt + 1}/{max_retries}...")
                    import asyncio
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                    
                else:
                    # Outros erros não-recuperáveis
                    logger.error(f"[PLATFORM-TOKEN-MANAGER] Erro inesperado da plataforma {platform} (status {resp.status_code}) para tenant_id={tenant_id}: {resp.text[:200]}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Falha na comunicação com a plataforma {platform} (status {resp.status_code})."
                    )
                    
            except httpx.RequestError as req_err:
                if attempt < max_retries - 1:
                    logger.warning(f"[PLATFORM-TOKEN-MANAGER] Erro de rede ao conectar com {platform}: {req_err}. Tentativa {attempt + 1}/{max_retries}...")
                    import asyncio
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                logger.error(f"[PLATFORM-TOKEN-MANAGER] Plataforma {platform} inacessível após retentativas: {req_err}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Serviço da plataforma {platform} inacessível. Verifique conectividade."
                )

        # Se chegou aqui, esgotou todas as tentativas
        logger.error(f"[PLATFORM-TOKEN-MANAGER] Não foi possível obter token da plataforma {platform} para tenant_id={tenant_id} após {max_retries} tentativas")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Não foi possível obter token de acesso da plataforma {platform}."
        )

    def invalidate(self, tenant_id: str, platform: str) -> None:
        """
        Remove o token do cache para forçar uma nova obtenção na próxima chamada.
        
        Args:
            tenant_id: ID do tenant
            platform: Nome da plataforma
        """
        self._cache.pop((tenant_id, platform), None)
        logger.info(f"[PLATFORM-TOKEN-MANAGER] Cache invalidado para tenant_id={tenant_id}, platform={platform}")


# Instância singleton do gerenciador de tokens de plataforma
platform_token_manager = PlatformTokenManager()