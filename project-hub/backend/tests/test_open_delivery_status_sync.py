"""Tests for Open Delivery status sync outbound."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import status
from sqlalchemy.orm import Session

from app.api.endpoints.orders import notify_platform_status
from app.models.order_manager import OrderManagerOrder
from app.models.tenant_platform_integration import TenantPlatformIntegration


class TestNotifyPlatformStatus:
    """Tests for the notify_platform_status function."""

    @pytest.mark.asyncio
    async def test_notify_platform_status_internal_order(self, db: Session):
        """
        Test: source_platform=None or external_order_id=None should return immediately (internal order).
        """
        tenant_id = "test_tenant"
        order_id = "test-order-123"
        new_status = "accepted"

        # Case 1: source_platform is None
        db_order = OrderManagerOrder(
            tenant_id=tenant_id,
            pedido_id=order_id,
            cliente_id="client-1",
            source_platform=None,  # internal order
            external_order_id="ext-123",
            status="pending"
        )
        db.add(db_order)
        db.commit()

        # Mock platform_token_manager.get_token to ensure it's not called
        with patch('app.api.endpoints.orders.platform_token_manager') as mock_ptm:
            mock_ptm.get_token = AsyncMock()
            await notify_platform_status(order_id, tenant_id, new_status, db)
            mock_ptm.get_token.assert_not_called()

        # Case 2: external_order_id is None
        db_order.external_order_id = None
        db.commit()

        with patch('app.api.endpoints.orders.platform_token_manager') as mock_ptm:
            mock_ptm.get_token = AsyncMock()
            await notify_platform_status(order_id, tenant_id, new_status, db)
            mock_ptm.get_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_platform_status_accepted(self, db: Session):
        """
        Test: external order with source_platform='pedidos10' should make POST to correct URL.
        """
        tenant_id = "test_tenant"
        order_id = "test-order-456"
        new_status = "accepted"
        external_order_id = "ext-order-789"
        source_platform = "pedidos10"
        base_url = "https://api.pedidos10.com"
        od_action = "confirm"  # from STATUS_OUTBOUND_MAP for 'accepted'
        expected_url = f"{base_url}/orders/{external_order_id}/{od_action}"

        # Create order in DB
        db_order = OrderManagerOrder(
            tenant_id=tenant_id,
            pedido_id=order_id,
            cliente_id="client-456",
            source_platform=source_platform,
            external_order_id=external_order_id,
            status="pending"
        )
        db.add(db_order)
        db.commit()

        # Create integration in DB
        integration = TenantPlatformIntegration(
            tenant_id=tenant_id,
            platform=source_platform,
            base_url=base_url,
            auth_url="https://auth.pedidos10.com/oauth/token",
            credentials_enc="{}",  # dummy
            is_active=True,
            merchant_id="merchant_123"
        )
        db.add(integration)
        db.commit()

        # Mock platform_token_manager.get_token to return a fake token
        fake_token = "fake-token-123"

        with patch('app.api.endpoints.orders.platform_token_manager') as mock_ptm, \
             patch('app.api.endpoints.orders.httpx.AsyncClient') as mock_client_class:
            mock_ptm.get_token = AsyncMock(return_value=fake_token)

            # Mock the HTTP client and response
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Call the function
            await notify_platform_status(order_id, tenant_id, new_status, db)

            # Assertions
            mock_ptm.get_token.assert_called_once_with(tenant_id, source_platform, db)
            mock_client_class.assert_called_once()
            mock_client.post.assert_called_once_with(
                expected_url,
                headers={"Authorization": f"Bearer {fake_token}"}
            )
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_platform_status_no_integration(self, db: Session):
        """
        Test: no active TenantPlatformIntegration should return without making POST.
        """
        tenant_id = "test_tenant"
        order_id = "test-order-999"
        new_status = "accepted"
        external_order_id = "ext-order-111"
        source_platform = "pedidos10"

        # Create order in DB
        db_order = OrderManagerOrder(
            tenant_id=tenant_id,
            pedido_id=order_id,
            cliente_id="client-999",
            source_platform=source_platform,
            external_order_id=external_order_id,
            status="pending"
        )
        db.add(db_order)
        db.commit()

        # Do NOT create integration (simulate missing)

        with patch('app.api.endpoints.orders.platform_token_manager') as mock_ptm, \
             patch('app.api.endpoints.orders.httpx.AsyncClient') as mock_client_class:
            mock_ptm.get_token = AsyncMock()
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await notify_platform_status(order_id, tenant_id, new_status, db)

            # Assertions
            mock_ptm.get_token.assert_not_called()
            mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_platform_status_http_error(self, db: Session):
        """
        Test: HTTP error should not raise exception (fail-safe).
        """
        tenant_id = "test_tenant"
        order_id = "test-order-http-err"
        new_status = "preparing"
        external_order_id = "ext-http-err"
        source_platform = "pedidos10"
        base_url = "https://api.pedidos10.com"
        od_action = "preparing"  # from STATUS_OUTBOUND_MAP for 'preparing'

        # Create order in DB
        db_order = OrderManagerOrder(
            tenant_id=tenant_id,
            pedido_id=order_id,
            cliente_id="client-http",
            source_platform=source_platform,
            external_order_id=external_order_id,
            status="accepted"
        )
        db.add(db_order)
        db.commit()

        # Create integration in DB
        integration = TenantPlatformIntegration(
            tenant_id=tenant_id,
            platform=source_platform,
            base_url=base_url,
            auth_url="https://auth.pedidos10.com/oauth/token",
            credentials_enc="{}",
            is_active=True,
            merchant_id="merchant_456"
        )
        db.add(integration)
        db.commit()

        # Mock platform_token_manager.get_token to return a fake token
        fake_token = "fake-token-http"

        with patch('app.api.endpoints.orders.platform_token_manager') as mock_ptm, \
             patch('app.api.endpoints.orders.httpx.AsyncClient') as mock_client_class, \
             patch('app.api.endpoints.orders.log_realtime_event') as mock_log:
            mock_ptm.get_token = AsyncMock(return_value=fake_token)

            # Mock the HTTP client to raise an exception
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("Internal Server Error")
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Call the function - should not raise
            await notify_platform_status(order_id, tenant_id, new_status, db)

            # Assertions
            mock_ptm.get_token.assert_called_once_with(tenant_id, source_platform, db)
            mock_client_class.assert_called_once()
            mock_client.post.assert_called_once_with(
                f"{base_url}/orders/{external_order_id}/{od_action}",
                headers={"Authorization": f"Bearer {fake_token}"}
            )
            # Should have logged the error
            mock_log.assert_called_once()
            # Check that the log event is for PLATFORM_NOTIFY_ERROR
            args, kwargs = mock_log.call_args
            assert args[0] == "PLATFORM_NOTIFY_ERROR"
            assert kwargs["tenant_id"] == tenant_id
            assert kwargs["pedido_id"] == order_id


class TestEndpointsTriggerPlatformNotify:
    """Test that the endpoints trigger the background task for platform notification."""

    def test_accept_order_triggers_platform_notify(self, db: Session):
        """
        Test: accept_order endpoint calls add_task with notify_platform_status for 'accepted'.
        """
        from app.api.endpoints.orders import accept_order

        tenant_id = "tenant-accept"
        order_id = "order-accept-test"

        db_order = OrderManagerOrder(
            tenant_id=tenant_id,
            pedido_id=order_id,
            cliente_id="client-123",
            source_platform="pedidos10",
            external_order_id="ext-accept-1",
            status="pending"
        )
        db.add(db_order)
        db.commit()

        mock_background_tasks = Mock()
        mock_request = Mock()

        with patch('app.api.endpoints.orders.get_operator_tenant_id', return_value=tenant_id), \
             patch('app.api.endpoints.orders.broadcast', new_callable=AsyncMock), \
             patch('app.api.endpoints.orders.retry_order_status_webhook', new_callable=AsyncMock), \
             patch('app.api.endpoints.orders.notify_platform_status', new_callable=AsyncMock) as mock_notify:
            import asyncio
            asyncio.run(accept_order(
                order_id=order_id,
                request=mock_request,
                background_tasks=mock_background_tasks,
                db=db
            ))

            assert mock_background_tasks.add_task.call_count == 2

            # Verify notify_platform_status was registered as a background task
            mock_notify.assert_not_called()  # Should be added as background task, not called directly
            calls = mock_background_tasks.add_task.call_args_list
            notify_call = None
            for call in calls:
                args, kwargs = call
                if args and args[0] is mock_notify:
                    notify_call = call
                    break

            assert notify_call is not None, "notify_platform_status task not found in add_task calls"
            args, kwargs = notify_call
            assert args[1] == order_id  # order_id (as str via str() in the endpoint)
            assert args[2] == tenant_id  # tenant_id
            assert args[3] == "accepted"  # new_status
            assert args[4] == db  # db session

    def test_reject_order_triggers_platform_notify(self, db: Session):
        """
        Test: reject_order endpoint calls add_task with notify_platform_status for 'rejected'.
        """
        from app.api.endpoints.orders import reject_order

        tenant_id = "tenant-reject"
        order_id = "order-reject-test"

        db_order = OrderManagerOrder(
            tenant_id=tenant_id,
            pedido_id=order_id,
            cliente_id="client-456",
            source_platform="pedidos10",
            external_order_id="ext-reject-1",
            status="pending"
        )
        db.add(db_order)
        db.commit()

        mock_background_tasks = Mock()
        mock_request = Mock()

        with patch('app.api.endpoints.orders.get_operator_tenant_id', return_value=tenant_id), \
             patch('app.api.endpoints.orders.broadcast', new_callable=AsyncMock), \
             patch('app.api.endpoints.orders.retry_order_status_webhook', new_callable=AsyncMock), \
             patch('app.api.endpoints.orders.notify_platform_status', new_callable=AsyncMock) as mock_notify:
            import asyncio
            asyncio.run(reject_order(
                order_id=order_id,
                request=mock_request,
                background_tasks=mock_background_tasks,
                db=db
            ))

            assert mock_background_tasks.add_task.call_count == 2
            mock_notify.assert_not_called()
            calls = mock_background_tasks.add_task.call_args_list
            notify_call = None
            for call in calls:
                args, kwargs = call
                if args and args[0] is mock_notify:
                    notify_call = call
                    break

            assert notify_call is not None, "notify_platform_status task not found in add_task calls"
            args, kwargs = notify_call
            assert args[1] == order_id
            assert args[2] == tenant_id
            assert args[3] == "rejected"
            assert args[4] == db

    def test_update_order_status_triggers_platform_notify(self, db: Session):
        """
        Test: update_order_status endpoint calls add_task with notify_platform_status for the new status.
        """
        from app.api.endpoints.orders import update_order_status

        tenant_id = "tenant-update"
        order_id = "order-update-test"
        new_status = "ready_for_delivery"

        db_order = OrderManagerOrder(
            tenant_id=tenant_id,
            pedido_id=order_id,
            cliente_id="client-789",
            source_platform="pedidos10",
            external_order_id="ext-update-1",
            status="preparing"
        )
        db.add(db_order)
        db.commit()

        mock_background_tasks = Mock()
        mock_request = Mock()

        with patch('app.api.endpoints.orders.get_operator_tenant_id', return_value=tenant_id), \
             patch('app.api.endpoints.orders.broadcast', new_callable=AsyncMock), \
             patch('app.api.endpoints.orders.retry_order_status_webhook', new_callable=AsyncMock), \
             patch('app.api.endpoints.orders.notify_platform_status', new_callable=AsyncMock) as mock_notify:
            import asyncio
            asyncio.run(update_order_status(
                order_id=order_id,
                request=mock_request,
                background_tasks=mock_background_tasks,
                order_status=new_status,
                db=db
            ))

            assert mock_background_tasks.add_task.call_count == 2
            mock_notify.assert_not_called()
            calls = mock_background_tasks.add_task.call_args_list
            notify_call = None
            for call in calls:
                args, kwargs = call
                if args and args[0] is mock_notify:
                    notify_call = call
                    break

            assert notify_call is not None, "notify_platform_status task not found in add_task calls"
            args, kwargs = notify_call
            assert args[1] == order_id
            assert args[2] == tenant_id
            assert args[3] == new_status
            assert args[4] == db