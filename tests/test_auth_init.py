"""Tests for auth_init script functionality."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add the scripts directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from auth_init import create_or_update_application_with_secret, update_azd_env
from auth_common import get_application


class MockApplication:
    """Mock Application object for testing."""
    def __init__(self, display_name="Test App"):
        self.display_name = display_name


class MockGraphClient:
    """Mock GraphServiceClient for testing."""
    def __init__(self):
        self.applications = Mock()
        self.applications_with_app_id = Mock()


@pytest.mark.asyncio
async def test_create_or_update_application_with_secret_regenerates_when_app_recreated():
    """Test that secrets are regenerated when applications are recreated."""
    
    # Mock environment variables - simulating the case where app was deleted but env vars remain
    with patch.dict(os.environ, {
        'AZURE_SERVER_APP_ID': 'old-app-id',
        'AZURE_SERVER_APP_SECRET': 'old-secret-from-deleted-app'
    }):
        
        # Mock graph client
        graph_client = MockGraphClient()
        
        # Mock get_application to return None (app doesn't exist anymore)
        with patch('auth_init.get_application', return_value=None):
            # Mock create_application to return new app details
            with patch('auth_init.create_application', return_value=('new-object-id', 'new-app-id')):
                # Mock add_client_secret to return new secret
                with patch('auth_init.add_client_secret', return_value='new-secret') as mock_add_secret:
                    # Mock update_azd_env to track environment updates
                    with patch('auth_init.update_azd_env') as mock_update_env:
                        
                        # Call the function
                        object_id, app_id, created_app = await create_or_update_application_with_secret(
                            graph_client,
                            app_id_env_var='AZURE_SERVER_APP_ID',
                            app_secret_env_var='AZURE_SERVER_APP_SECRET',
                            request_app=MockApplication()
                        )
                        
                        # Verify that a new application was created
                        assert created_app is True
                        assert object_id == 'new-object-id'
                        assert app_id == 'new-app-id'
                        
                        # Verify that add_client_secret was called (secret was regenerated)
                        mock_add_secret.assert_called_once_with(graph_client, 'new-object-id')
                        
                        # Verify that the environment was updated with the new secret
                        mock_update_env.assert_any_call('AZURE_SERVER_APP_SECRET', 'new-secret')


@pytest.mark.asyncio
async def test_create_or_update_application_with_secret_skips_when_app_exists_and_secret_exists():
    """Test that secrets are NOT regenerated when app exists and secret exists."""
    
    # Mock environment variables - app and secret both exist
    with patch.dict(os.environ, {
        'AZURE_SERVER_APP_ID': 'existing-app-id',
        'AZURE_SERVER_APP_SECRET': 'existing-secret'
    }):
        
        # Mock graph client
        graph_client = MockGraphClient()
        graph_client.applications.by_application_id.return_value.patch = AsyncMock()
        
        # Mock get_application to return existing app
        with patch('auth_init.get_application', return_value='existing-object-id'):
            # Mock add_client_secret (should not be called)
            with patch('auth_init.add_client_secret') as mock_add_secret:
                # Mock update_azd_env to track environment updates
                with patch('auth_init.update_azd_env') as mock_update_env:
                    
                    # Call the function
                    object_id, app_id, created_app = await create_or_update_application_with_secret(
                        graph_client,
                        app_id_env_var='AZURE_SERVER_APP_ID',
                        app_secret_env_var='AZURE_SERVER_APP_SECRET',
                        request_app=MockApplication()
                    )
                    
                    # Verify that no new application was created
                    assert created_app is False
                    assert object_id == 'existing-object-id'
                    assert app_id == 'existing-app-id'
                    
                    # Verify that add_client_secret was NOT called (secret was not regenerated)
                    mock_add_secret.assert_not_called()
                    
                    # Verify that the environment was NOT updated with a new secret
                    mock_update_env.assert_not_called()


@pytest.mark.asyncio
async def test_create_or_update_application_with_secret_generates_when_app_exists_but_no_secret():
    """Test that secrets are generated when app exists but no secret exists."""
    
    # Mock environment variables - app exists but no secret
    with patch.dict(os.environ, {
        'AZURE_SERVER_APP_ID': 'existing-app-id'
    }, clear=False):
        # Ensure the secret env var is not set
        if 'AZURE_SERVER_APP_SECRET' in os.environ:
            del os.environ['AZURE_SERVER_APP_SECRET']
        
        # Mock graph client
        graph_client = MockGraphClient()
        graph_client.applications.by_application_id.return_value.patch = AsyncMock()
        
        # Mock get_application to return existing app
        with patch('auth_init.get_application', return_value='existing-object-id'):
            # Mock add_client_secret to return new secret
            with patch('auth_init.add_client_secret', return_value='new-secret') as mock_add_secret:
                # Mock update_azd_env to track environment updates
                with patch('auth_init.update_azd_env') as mock_update_env:
                    
                    # Call the function
                    object_id, app_id, created_app = await create_or_update_application_with_secret(
                        graph_client,
                        app_id_env_var='AZURE_SERVER_APP_ID',
                        app_secret_env_var='AZURE_SERVER_APP_SECRET',
                        request_app=MockApplication()
                    )
                    
                    # Verify that no new application was created
                    assert created_app is False
                    assert object_id == 'existing-object-id'
                    assert app_id == 'existing-app-id'
                    
                    # Verify that add_client_secret was called (secret was generated)
                    mock_add_secret.assert_called_once_with(graph_client, 'existing-object-id')
                    
                    # Verify that the environment was updated with the new secret
                    mock_update_env.assert_called_once_with('AZURE_SERVER_APP_SECRET', 'new-secret')


async def run_tests():
    """Run all tests."""
    print("Running test_create_or_update_application_with_secret_regenerates_when_app_recreated...")
    await test_create_or_update_application_with_secret_regenerates_when_app_recreated()
    print("✅ PASSED")
    
    print("Running test_create_or_update_application_with_secret_skips_when_app_exists_and_secret_exists...")
    await test_create_or_update_application_with_secret_skips_when_app_exists_and_secret_exists()
    print("✅ PASSED")
    
    print("Running test_create_or_update_application_with_secret_generates_when_app_exists_but_no_secret...")
    await test_create_or_update_application_with_secret_generates_when_app_exists_but_no_secret()
    print("✅ PASSED")
    
    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())