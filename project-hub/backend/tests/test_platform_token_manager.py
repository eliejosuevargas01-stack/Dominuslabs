"""
Testes para PlatformTokenManager
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
import httpx

from app.services.platform_token_manager import PlatformTokenManager


class TestPlatformTokenManager:
    """Testes para o PlatformTokenManager"""
    
    @pytest.fixture
    def fresh_manager(self):
        """Cria uma nova instância do gerenciador para cada teste"""
        return PlatformTokenManager()
    
    @pytest.mark.asyncio
    async def test_get_token_cache_hit(self, db, fresh_manager):
        """Teste: segundo get_token usa cache, não faz HTTP"""
        tenant_id = "tenant123"
        platform = "pedidos10"
        
        # Mock da integração no banco
        mock_integration = Mock()
        mock_integration.auth_url = "https://api.pedidos10.com"
        mock_integration.credentials_enc = "encrypted_credentials"
        
        with patch('app.services.platform_token_manager.decrypt_credentials') as mock_decrypt:
            mock_decrypt.return_value = {"client_id": "test_client", "client_secret": "test_secret"}
            
            with patch.object(db, 'query') as mock_query:
                mock_query.return_value.filter.return_value.first.return_value = mock_integration
                
                # Mock do httpx client para a primeira chamada
                with patch('app.services.platform_token_manager.get_async_client') as mock_get_client:
                    mock_client = AsyncMock()
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"access_token": "cached_token_123"}
                    mock_client.post.return_value = mock_response
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    
                    # Primeira chamada - deve fazer HTTP
                    token1 = await fresh_manager.get_token(tenant_id, platform, db)
                    
                    # Segunda chamada - deve usar cache
                    token2 = await fresh_manager.get_token(tenant_id, platform, db)
                    
                    assert token1 == "cached_token_123"
                    assert token2 == "cached_token_123"
                    assert token1 == token2
                    
                    # Verifica que o HTTP foi chamado apenas uma vez (cache hit na segunda chamada)
                    assert mock_client.post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_token_no_integration(self, db, fresh_manager):
        """Teste: retorna HTTPException 503 quando não há integração no DB"""
        tenant_id = "tenant123"
        platform = "pedidos10"
        
        with patch.object(db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await fresh_manager.get_token(tenant_id, platform, db)
            
            assert exc_info.value.status_code == 503
            assert "não configurada" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_token_invalid_credentials(self, db, fresh_manager):
        """Teste: retorna HTTPException 503 quando plataforma retorna 401/403"""
        tenant_id = "tenant123"
        platform = "pedidos10"
        
        # Mock da integração
        mock_integration = Mock()
        mock_integration.auth_url = "https://api.pedidos10.com"
        mock_integration.credentials_enc = "encrypted_credentials"
        
        with patch('app.services.platform_token_manager.decrypt_credentials') as mock_decrypt:
            mock_decrypt.return_value = {"client_id": "test_client", "client_secret": "test_secret"}
            
            with patch.object(db, 'query') as mock_query:
                mock_query.return_value.filter.return_value.first.return_value = mock_integration
                
                # Mock do httpx client retornando 401
                with patch('app.services.platform_token_manager.get_async_client') as mock_get_client:
                    mock_client = AsyncMock()
                    mock_response = Mock()
                    mock_response.status_code = 401
                    mock_response.text = "Unauthorized"
                    mock_client.post.return_value = mock_response
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    
                    with pytest.raises(HTTPException) as exc_info:
                        await fresh_manager.get_token(tenant_id, platform, db)
                    
                    assert exc_info.value.status_code == 503
                    assert "Credenciais inválidas" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_token_retry_then_success(self, db, fresh_manager):
        """Teste: falha 2x, sucesso na 3a tentativa"""
        tenant_id = "tenant123"
        platform = "pedidos10"
        
        # Mock da integração
        mock_integration = Mock()
        mock_integration.auth_url = "https://api.pedidos10.com"
        mock_integration.credentials_enc = "encrypted_credentials"
        
        with patch('app.services.platform_token_manager.decrypt_credentials') as mock_decrypt:
            mock_decrypt.return_value = {"client_id": "test_client", "client_secret": "test_secret"}
            
            with patch.object(db, 'query') as mock_query:
                mock_query.return_value.filter.return_value.first.return_value = mock_integration
                
                # Mock do httpx client: primeira e segunda tentativas falham, terceira sucesso
                with patch('app.services.platform_token_manager.get_async_client') as mock_get_client:
                    mock_client = AsyncMock()
                    
                    # Primeira chamada: 503
                    mock_response_503 = Mock()
                    mock_response_503.status_code = 503
                    mock_response_503.text = "Service Unavailable"
                    
                    # Segunda chamada: 503
                    mock_response_503_2 = Mock()
                    mock_response_503_2.status_code = 503
                    mock_response_503_2.text = "Service Unavailable"
                    
                    # Terceira chamada: sucesso
                    mock_response_200 = Mock()
                    mock_response_200.status_code = 200
                    mock_response_200.json.return_value = {"access_token": "retry_success_token"}
                    
                    mock_client.post.side_effect = [
                        mock_response_503,
                        mock_response_503_2,
                        mock_response_200
                    ]
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    
                    # Deve tentar 3 vezes e obter sucesso na terceira
                    token = await fresh_manager.get_token(tenant_id, platform, db)
                    
                    assert token == "retry_success_token"
                    assert mock_client.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_invalidate(self, fresh_manager):
        """Teste: remove do cache"""
        tenant_id = "tenant123"
        platform = "pedidos10"
        cache_key = (tenant_id, platform)
        
        # Adiciona algo ao cache
        fresh_manager._cache[cache_key] = "some_token"
        assert cache_key in fresh_manager._cache
        
        # Invalida o cache
        fresh_manager.invalidate(tenant_id, platform)
        
        # Verifica que foi removido
        assert cache_key not in fresh_manager._cache