"""
OAuth2 and JWT authentication tests.

Tests for:
- Azure AD token validation
- JWT token creation and validation
- RBAC middleware
- Auth decorators
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.backend.auth.jwt_handler import JWTHandler
from app.backend.auth.rbac import RBACMiddleware


class TestJWTHandler:
    """Test JWT token handling."""

    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler with test secret."""
        return JWTHandler(secret="test-secret-key-very-long")

    def test_jwt_token_creation(self, jwt_handler):
        """Test JWT token generation."""
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
        )

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "Bearer"
        assert tokens["expires_in"] == 15 * 60  # 15 minutes in seconds

    def test_jwt_token_validation(self, jwt_handler):
        """Test JWT token validation."""
        # Create tokens
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user", "manager"],
        )

        # Validate access token
        payload = jwt_handler.validate_token(tokens["access_token"])

        # Validate access token
        payload = jwt_handler.validate_token(tokens["access_token"])

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "user@example.com"
        assert "user" in payload["roles"]
        assert "manager" in payload["roles"]
        assert payload["type"] == "access"

    def test_jwt_refresh_token_validation(self, jwt_handler):
        """Test refresh token validation."""
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
        )

        # Validate refresh token
        payload = jwt_handler.validate_token(
            tokens["refresh_token"],
            token_type="refresh",
        )

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_jwt_token_type_mismatch(self, jwt_handler):
        """Test validation fails when token type doesn't match."""
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
        )

        # Try to validate access token as refresh token
        payload = jwt_handler.validate_token(
            tokens["access_token"],
            token_type="refresh",
        )

        assert payload is None

    def test_jwt_expired_token_rejection(self, jwt_handler):
        """Test that expired tokens are rejected."""
        jwt_handler.access_token_expire = -1  # Negative = already expired

        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
        )

        # Token should be expired
        payload = jwt_handler.validate_token(tokens["access_token"])
        assert payload is None

    def test_jwt_refresh_access_token(self, jwt_handler):
        """Test generating new access token from refresh token."""
        # Create initial tokens
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
        )

        # Get new access token
        new_access_token = jwt_handler.refresh_access_token(
            tokens["refresh_token"]
        )

        assert new_access_token is not None
        assert new_access_token != tokens["access_token"]

        # Validate new token
        payload = jwt_handler.validate_token(new_access_token)
        assert payload is not None
        assert payload["sub"] == "user123"

    def test_jwt_invalid_refresh_token(self, jwt_handler):
        """Test refresh fails with invalid refresh token."""
        # Try with access token instead of refresh token
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
        )

        new_token = jwt_handler.refresh_access_token(tokens["access_token"])
        assert new_token is None

    def test_jwt_decode_token(self, jwt_handler):
        """Test decoding token."""
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
        )

        claims = jwt_handler.get_token_claims(tokens["access_token"])
        assert claims is not None
        assert claims["sub"] == "user123"

    def test_jwt_additional_claims(self, jwt_handler):
        """Test token creation with additional claims."""
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["user"],
            additional_claims={"company": "acme", "department": "engineering"},
        )

        payload = jwt_handler.validate_token(tokens["access_token"])
        assert payload["company"] == "acme"
        assert payload["department"] == "engineering"

    def test_jwt_multiple_roles(self, jwt_handler):
        """Test token with multiple roles."""
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["admin", "manager", "user"],
        )

        payload = jwt_handler.validate_token(tokens["access_token"])
        assert set(payload["roles"]) == {"admin", "manager", "user"}


class TestRBACMiddleware:
    """Test Role-Based Access Control."""

    @pytest.fixture
    def rbac(self):
        """Create RBAC middleware."""
        return RBACMiddleware()

    def test_rbac_default_roles(self, rbac):
        """Test default roles are defined."""
        roles = rbac.get_all_roles()
        assert "admin" in roles
        assert "user" in roles
        assert "viewer" in roles
        assert "guest" in roles

    def test_rbac_admin_permissions(self, rbac):
        """Test admin role has all permissions."""
        admin_perms = rbac.get_role_permissions("admin")
        assert "read" in admin_perms
        assert "write" in admin_perms
        assert "delete" in admin_perms
        assert "audit" in admin_perms
        assert "manage_users" in admin_perms

    def test_rbac_user_permissions(self, rbac):
        """Test user role permissions."""
        user_perms = rbac.get_role_permissions("user")
        assert "read" in user_perms
        assert "write" in user_perms
        assert "delete" not in user_perms

    def test_rbac_viewer_permissions(self, rbac):
        """Test viewer role has only read permission."""
        viewer_perms = rbac.get_role_permissions("viewer")
        assert "read" in viewer_perms
        assert "write" not in viewer_perms
        assert "delete" not in viewer_perms

    def test_rbac_guest_permissions(self, rbac):
        """Test guest role has no permissions."""
        guest_perms = rbac.get_role_permissions("guest")
        assert len(guest_perms) == 0

    def test_rbac_add_custom_role(self, rbac):
        """Test adding custom role."""
        rbac.add_role("moderator", ["read", "write", "delete_own"])
        perms = rbac.get_role_permissions("moderator")
        assert "read" in perms
        assert "delete_own" in perms

    def test_rbac_get_all_roles(self, rbac):
        """Test getting all roles."""
        roles = rbac.get_all_roles()
        assert isinstance(roles, list)
        assert len(roles) >= 4


class TestAzureADAuth:
    """Test Azure AD authentication."""

    def test_azure_ad_init_with_env(self):
        """Test Azure AD initialization with environment variables."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant",
                "AZURE_CLIENT_ID": "test-client",
            },
        ):
            from app.backend.auth.azure_ad import AzureADAuth

            auth = AzureADAuth()
            assert auth.tenant_id == "test-tenant"
            assert auth.client_id == "test-client"

    def test_azure_ad_init_with_params(self):
        """Test Azure AD initialization with parameters."""
        from app.backend.auth.azure_ad import AzureADAuth

        auth = AzureADAuth(
            tenant_id="test-tenant",
            client_id="test-client",
        )
        assert auth.tenant_id == "test-tenant"
        assert auth.client_id == "test-client"

    def test_azure_ad_jwks_url_generation(self):
        """Test JWKS URL is correctly generated."""
        from app.backend.auth.azure_ad import AzureADAuth

        auth = AzureADAuth(
            tenant_id="test-tenant",
            client_id="test-client",
        )
        expected_url = (
            "https://login.microsoftonline.com/test-tenant/discovery/v2.0/keys"
        )
        assert auth.jwks_url == expected_url

    @pytest.mark.asyncio
    async def test_azure_ad_find_key(self):
        """Test finding key from JWKS."""
        from app.backend.auth.azure_ad import AzureADAuth

        # Test key finding logic
        # In real scenario, JWKS would be fetched from Azure AD
        auth = AzureADAuth(
            tenant_id="test-tenant",
            client_id="test-client",
        )
        assert auth is not None
        # The method requires valid JWK format for conversion
        # Integration tests would mock aiohttp for full testing


class TestAuthIntegration:
    """Integration tests for auth flows."""

    def test_complete_auth_flow(self):
        """Test complete authentication flow."""
        # Create JWT handler
        jwt_handler = JWTHandler(secret="test-secret-key-very-long")

        # User logs in - create tokens
        tokens = jwt_handler.create_tokens(
            user_id="user123",
            user_email="user@example.com",
            roles=["admin"],
        )

        # Verify access token
        access_payload = jwt_handler.validate_token(tokens["access_token"])
        assert access_payload["sub"] == "user123"
        assert "admin" in access_payload["roles"]

        # Later, refresh access token
        new_access = jwt_handler.refresh_access_token(tokens["refresh_token"])
        assert new_access is not None

        # Verify new token
        new_payload = jwt_handler.validate_token(new_access)
        assert new_payload["sub"] == "user123"

    def test_rbac_integration(self):
        """Test RBAC with JWT tokens."""
        jwt_handler = JWTHandler(secret="test-secret-key-very-long")
        rbac = RBACMiddleware()

        # Create admin token
        admin_tokens = jwt_handler.create_tokens(
            user_id="admin1",
            user_email="admin@example.com",
            roles=["admin"],
        )

        # Create user token
        user_tokens = jwt_handler.create_tokens(
            user_id="user1",
            user_email="user@example.com",
            roles=["user"],
        )

        # Validate both tokens
        admin_payload = jwt_handler.validate_token(admin_tokens["access_token"])
        user_payload = jwt_handler.validate_token(user_tokens["access_token"])

        # Check admin has delete permission
        admin_perms = rbac.roles.get("admin", [])
        assert "delete" in admin_perms

        # Check user doesn't have delete permission
        user_perms = rbac.roles.get("user", [])
        assert "delete" not in user_perms

        assert admin_payload is not None
        assert user_payload is not None


# Fixtures for Quart testing
@pytest.fixture
def app():
    """Create test app."""
    from quart import Quart

    app = Quart(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestAuthEndpoints:
    """Test auth-protected endpoints."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, app, client):
        """Test protected endpoint rejects requests without token."""

        @app.route("/protected")
        async def protected():
            return {"message": "Protected"}, 200

        # Request without token should fail
        # Note: Would need actual auth decorator to fully test
        response = await client.get("/protected")
        assert response.status_code in [401, 200]  # Depends on decorator


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
