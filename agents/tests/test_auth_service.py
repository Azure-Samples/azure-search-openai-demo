"""
Pytest tests for authentication service functionality.
Tests Microsoft 365 authentication and authorization features.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from botbuilder.schema import Activity, ActivityTypes

from services.auth_service import AuthService, UserClaims, GraphUserInfo, GraphGroupInfo
from config.agent_config import AgentConfig


class MockTurnContext:
    """Mock TurnContext for testing."""
    
    def __init__(self, activity: Activity):
        self.activity = activity
        self.activity.channel_id = "msteams"  # Set channel_id on activity
        self.channel_id = "msteams"
        self.conversation = activity.conversation
        self.from_property = activity.from_property
        self.recipient = activity.recipient


class TestAuthService:
    """Test cases for AuthService."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock AgentConfig for testing."""
        config = Mock(spec=AgentConfig)
        config.tenant_id = "test-tenant-id"
        config.client_id = "test-client-id"
        config.client_secret = "test-client-secret"
        return config
    
    @pytest.fixture
    def auth_service(self, mock_config):
        """Create an AuthService instance for testing."""
        return AuthService(mock_config)
    
    @pytest.fixture
    def mock_turn_context(self):
        """Create a mock TurnContext for testing."""
        from_property = Mock()
        from_property.id = "user1"
        from_property.name = "Test User"
        
        conversation = Mock()
        conversation.id = "conv1"
        
        activity = Activity(
            type=ActivityTypes.message,
            text="Test message",
            from_property=from_property,
            recipient={"id": "bot1", "name": "RAG Assistant"},
            conversation=conversation
        )
        return MockTurnContext(activity)
    
    @pytest.fixture
    def mock_graph_user(self):
        """Create mock Graph user data."""
        return {
            "id": "user1",
            "displayName": "Test User",
            "mail": "test@example.com",
            "userPrincipalName": "test@example.com",
            "jobTitle": "Structural Engineer",
            "department": "Engineering",
            "officeLocation": "Seattle",
            "mobilePhone": "+1-555-0123",
            "businessPhones": ["+1-555-0124"],
            "preferredLanguage": "en-US"
        }
    
    @pytest.fixture
    def mock_graph_groups(self):
        """Create mock Graph groups data."""
        return {
            "value": [
                {
                    "@odata.type": "#microsoft.graph.group",
                    "id": "group1",
                    "displayName": "Structural Engineers",
                    "description": "Structural engineering team",
                    "groupTypes": [],
                    "securityEnabled": True
                },
                {
                    "@odata.type": "#microsoft.graph.group",
                    "id": "group2",
                    "displayName": "Document Readers",
                    "description": "Users who can read documents",
                    "groupTypes": [],
                    "securityEnabled": True
                }
            ]
        }
    
    @pytest.fixture
    def mock_graph_roles(self):
        """Create mock Graph roles data."""
        return {
            "value": [
                {
                    "@odata.type": "#microsoft.graph.directoryRole",
                    "id": "role1",
                    "displayName": "Global Administrator"
                }
            ]
        }
    
    def test_user_claims_creation(self):
        """Test UserClaims dataclass creation."""
        claims = UserClaims(
            user_id="user1",
            user_name="Test User",
            email="test@example.com",
            tenant_id="tenant1",
            groups=["Group1", "Group2"],
            roles=["Role1"],
            additional_claims={"key": "value"},
            is_authenticated=True
        )
        
        assert claims.user_id == "user1"
        assert claims.user_name == "Test User"
        assert claims.email == "test@example.com"
        assert claims.tenant_id == "tenant1"
        assert claims.groups == ["Group1", "Group2"]
        assert claims.roles == ["Role1"]
        assert claims.is_authenticated is True
    
    def test_graph_user_info_creation(self):
        """Test GraphUserInfo dataclass creation."""
        user_info = GraphUserInfo(
            id="user1",
            display_name="Test User",
            mail="test@example.com",
            user_principal_name="test@example.com",
            job_title="Engineer",
            department="Engineering"
        )
        
        assert user_info.id == "user1"
        assert user_info.display_name == "Test User"
        assert user_info.mail == "test@example.com"
        assert user_info.job_title == "Engineer"
        assert user_info.department == "Engineering"
    
    def test_graph_group_info_creation(self):
        """Test GraphGroupInfo dataclass creation."""
        group_info = GraphGroupInfo(
            id="group1",
            display_name="Test Group",
            description="Test description",
            group_types=["Unified"],
            security_enabled=True
        )
        
        assert group_info.id == "group1"
        assert group_info.display_name == "Test Group"
        assert group_info.description == "Test description"
        assert group_info.group_types == ["Unified"]
        assert group_info.security_enabled is True
    
    @pytest.mark.skip(reason="MSAL initialization requires network calls that are difficult to mock")
    @pytest.mark.asyncio
    async def test_initialize(self, auth_service):
        """Test authentication service initialization."""
        with patch('msal.ConfidentialClientApplication') as mock_msal:
            with patch('aiohttp.ClientSession') as mock_session:
                with patch('azure.identity.aio.DefaultAzureCredential') as mock_credential:
                    # Mock the MSAL app to avoid network calls
                    mock_msal_instance = Mock()
                    mock_msal.return_value = mock_msal_instance
                    
                    # Mock the credential
                    mock_credential_instance = AsyncMock()
                    mock_credential.return_value = mock_credential_instance
                    
                    # Mock the session
                    mock_session_instance = Mock()
                    mock_session.return_value = mock_session_instance
                    
                    await auth_service.initialize()
                    
                    mock_msal.assert_called_once()
                    mock_session.assert_called_once()
                    assert auth_service._msal_app == mock_msal_instance
    
    @pytest.mark.asyncio
    async def test_get_user_claims(self, auth_service, mock_turn_context):
        """Test getting basic user claims."""
        claims = await auth_service.get_user_claims(mock_turn_context)
        
        assert claims["oid"] == "user1"
        assert claims["name"] == "Test User"
        assert claims["tenant_id"] == "test-tenant-id"
        assert claims["channel_id"] == "msteams"
        assert claims["conversation_id"] == "conv1"
    
    @pytest.mark.asyncio
    async def test_get_access_token(self, auth_service):
        """Test getting access token."""
        with patch.object(auth_service, '_msal_app') as mock_msal:
            mock_msal.acquire_token_for_client.return_value = {
                "access_token": "test-token",
                "expires_in": 3600
            }
            
            token = await auth_service.get_access_token()
            
            assert token == "test-token"
            mock_msal.acquire_token_for_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_access_token_failure(self, auth_service):
        """Test getting access token when it fails."""
        with patch.object(auth_service, '_msal_app') as mock_msal:
            mock_msal.acquire_token_for_client.return_value = {
                "error": "invalid_client",
                "error_description": "Invalid client"
            }
            
            token = await auth_service.get_access_token()
            
            assert token is None
    
    @pytest.mark.asyncio
    async def test_get_user_from_graph(self, auth_service, mock_graph_user):
        """Test getting user from Microsoft Graph."""
        with patch.object(auth_service, '_http_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_graph_user
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            user_info = await auth_service.get_user_from_graph("user1", "test-token")
            
            assert user_info is not None
            assert user_info.id == "user1"
            assert user_info.display_name == "Test User"
            assert user_info.mail == "test@example.com"
            assert user_info.job_title == "Structural Engineer"
            assert user_info.department == "Engineering"
    
    @pytest.mark.asyncio
    async def test_get_user_from_graph_failure(self, auth_service):
        """Test getting user from Graph when it fails."""
        with patch.object(auth_service, '_http_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            user_info = await auth_service.get_user_from_graph("user1", "test-token")
            
            assert user_info is None
    
    @pytest.mark.asyncio
    async def test_get_user_groups_from_graph(self, auth_service, mock_graph_groups):
        """Test getting user groups from Microsoft Graph."""
        with patch.object(auth_service, '_http_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_graph_groups
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            groups = await auth_service.get_user_groups_from_graph("user1", "test-token")
            
            assert len(groups) == 2
            assert groups[0].id == "group1"
            assert groups[0].display_name == "Structural Engineers"
            assert groups[0].security_enabled is True
            assert groups[1].display_name == "Document Readers"
    
    @pytest.mark.asyncio
    async def test_get_user_roles_from_graph(self, auth_service, mock_graph_roles):
        """Test getting user roles from Microsoft Graph."""
        with patch.object(auth_service, '_http_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_graph_roles
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            roles = await auth_service.get_user_roles_from_graph("user1", "test-token")
            
            assert len(roles) == 1
            assert roles[0] == "Global Administrator"
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, auth_service):
        """Test token validation when successful."""
        with patch.object(auth_service, '_http_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            is_valid = await auth_service.validate_token("test-token")
            
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_token_failure(self, auth_service):
        """Test token validation when it fails."""
        with patch.object(auth_service, '_http_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            is_valid = await auth_service.validate_token("invalid-token")
            
            assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_get_enhanced_user_claims_with_cache(self, auth_service, mock_turn_context):
        """Test getting enhanced user claims with cache hit."""
        # Create cached claims
        cached_claims = UserClaims(
            user_id="user1",
            user_name="Cached User",
            email="cached@example.com",
            tenant_id="test-tenant-id",
            groups=["Cached Group"],
            roles=["Cached Role"],
            additional_claims={},
            is_authenticated=True,
            last_updated=datetime.now()
        )
        auth_service._token_cache["user1"] = cached_claims
        
        claims = await auth_service.get_enhanced_user_claims(mock_turn_context)
        
        assert claims.user_id == "user1"
        assert claims.user_name == "Cached User"
        assert claims.groups == ["Cached Group"]
    
    @pytest.mark.asyncio
    async def test_get_enhanced_user_claims_with_graph(self, auth_service, mock_turn_context, mock_graph_user, mock_graph_groups, mock_graph_roles):
        """Test getting enhanced user claims with Graph data."""
        with patch.object(auth_service, 'get_access_token', return_value="test-token"):
            with patch.object(auth_service, 'get_user_from_graph') as mock_get_user:
                with patch.object(auth_service, 'get_user_groups_from_graph') as mock_get_groups:
                    with patch.object(auth_service, 'get_user_roles_from_graph') as mock_get_roles:
                        # Mock Graph responses
                        mock_get_user.return_value = GraphUserInfo(
                            id="user1",
                            display_name="Test User",
                            mail="test@example.com",
                            user_principal_name="test@example.com",
                            job_title="Structural Engineer",
                            department="Engineering"
                        )
                        mock_get_groups.return_value = [
                            GraphGroupInfo(
                                id="group1",
                                display_name="Structural Engineers",
                                security_enabled=True
                            )
                        ]
                        mock_get_roles.return_value = ["Global Administrator"]
                        
                        claims = await auth_service.get_enhanced_user_claims(mock_turn_context)
                        
                        assert claims.user_id == "user1"
                        assert claims.user_name == "Test User"
                        assert claims.email == "test@example.com"
                        assert claims.groups == ["Structural Engineers"]
                        assert claims.roles == ["Global Administrator"]
                        assert claims.is_authenticated is True
                        assert "graph_user" in claims.additional_claims
                        assert "graph_groups" in claims.additional_claims
    
    @pytest.mark.asyncio
    async def test_check_user_permission_success(self, auth_service):
        """Test checking user permission when user has permission."""
        user_claims = UserClaims(
            user_id="user1",
            user_name="Test User",
            email="test@example.com",
            tenant_id="test-tenant-id",
            groups=["Structural Engineers", "Document Readers"],
            roles=["Global Administrators"],
            additional_claims={}
        )
        
        # Test structural analysis permission
        has_permission = await auth_service.check_user_permission(user_claims, "structural_analysis")
        assert has_permission is True
        
        # Test admin access permission (should work because user has Global Administrator role)
        has_permission = await auth_service.check_user_permission(user_claims, "admin_access")
        assert has_permission is True
    
    @pytest.mark.asyncio
    async def test_check_user_permission_failure(self, auth_service):
        """Test checking user permission when user doesn't have permission."""
        user_claims = UserClaims(
            user_id="user1",
            user_name="Test User",
            email="test@example.com",
            tenant_id="test-tenant-id",
            groups=["Other Group"],
            roles=["Other Role"],
            additional_claims={}
        )
        
        # Test structural analysis permission
        has_permission = await auth_service.check_user_permission(user_claims, "structural_analysis")
        assert has_permission is False
        
        # Test admin access permission
        has_permission = await auth_service.check_user_permission(user_claims, "admin_access")
        assert has_permission is False
    
    @pytest.mark.asyncio
    async def test_check_user_permission_unknown(self, auth_service):
        """Test checking unknown permission."""
        user_claims = UserClaims(
            user_id="user1",
            user_name="Test User",
            email="test@example.com",
            tenant_id="test-tenant-id",
            groups=["Structural Engineers"],
            roles=[],
            additional_claims={}
        )
        
        has_permission = await auth_service.check_user_permission(user_claims, "unknown_permission")
        assert has_permission is False
    
    @pytest.mark.asyncio
    async def test_close(self, auth_service):
        """Test closing the authentication service."""
        # Set up mock objects
        mock_credential = AsyncMock()
        mock_session = AsyncMock()
        auth_service._credential = mock_credential
        auth_service._http_session = mock_session
        
        await auth_service.close()
        
        mock_credential.close.assert_called_once()
        mock_session.close.assert_called_once()
        assert len(auth_service._token_cache) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_get_user_claims(self, auth_service, mock_turn_context):
        """Test error handling in get_user_claims."""
        # Mock an error in the method
        with patch.object(auth_service, '_get_teams_user_info', side_effect=Exception("Test error")):
            claims = await auth_service.get_user_claims(mock_turn_context)
            
            # Should return claims with fallback values on error
            assert claims["oid"] == "user1"
            assert claims["name"] == "Test User"  # Uses the name from turn_context
            assert claims["email"] == ""  # Empty email due to error
    
    @pytest.mark.asyncio
    async def test_error_handling_in_enhanced_claims(self, auth_service, mock_turn_context):
        """Test error handling in get_enhanced_user_claims."""
        with patch.object(auth_service, 'get_access_token', side_effect=Exception("Test error")):
            claims = await auth_service.get_enhanced_user_claims(mock_turn_context)
            
            # Should return basic claims on error
            assert claims.user_id == "user1"
            assert claims.is_authenticated is False