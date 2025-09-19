"""
Authentication Service for Microsoft 365 Agent.
This service handles authentication and authorization for the agent.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from botbuilder.core import TurnContext
from azure.identity.aio import DefaultAzureCredential
from msal import ConfidentialClientApplication
import aiohttp

from config.agent_config import AgentConfig


logger = logging.getLogger(__name__)


@dataclass
class UserClaims:
    """User claims from Microsoft 365 authentication."""
    user_id: str
    user_name: str
    email: str
    tenant_id: str
    groups: List[str]
    roles: List[str]
    additional_claims: Dict[str, Any]
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    is_authenticated: bool = False
    last_updated: Optional[datetime] = None


@dataclass
class GraphUserInfo:
    """Microsoft Graph user information."""
    id: str
    display_name: str
    mail: str
    user_principal_name: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    office_location: Optional[str] = None
    mobile_phone: Optional[str] = None
    business_phones: List[str] = None
    preferred_language: Optional[str] = None


@dataclass
class GraphGroupInfo:
    """Microsoft Graph group information."""
    id: str
    display_name: str
    description: Optional[str] = None
    group_types: List[str] = None
    security_enabled: bool = False


class AuthService:
    """
    Authentication Service that handles Microsoft 365 authentication and authorization.
    Integrates with existing authentication system while providing agent-specific functionality.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self._credential = DefaultAzureCredential()
        self._msal_app: Optional[ConfidentialClientApplication] = None
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._token_cache: Dict[str, UserClaims] = {}
        self._graph_base_url = "https://graph.microsoft.com/v1.0"
    
    async def initialize(self) -> None:
        """Initialize the authentication service."""
        try:
            # Initialize MSAL application for token validation
            self._msal_app = ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=f"https://login.microsoftonline.com/{self.config.tenant_id}"
            )
            
            # Initialize HTTP session for Microsoft Graph calls
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "Microsoft365Agent/1.0"
                }
            )
            
            logger.info("Auth Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Auth Service: {e}")
            raise
    
    async def get_user_claims(self, turn_context: TurnContext) -> Dict[str, Any]:
        """
        Get user claims from the turn context.
        This method extracts user information from the Microsoft 365 context.
        """
        try:
            # Extract basic user information from the turn context
            user_id = turn_context.activity.from_property.id
            user_name = turn_context.activity.from_property.name or "Unknown User"
            
            # For Teams, we can get additional user information
            if turn_context.activity.channel_id == "msteams":
                try:
                    # Get Teams user information
                    teams_info = await self._get_teams_user_info(turn_context)
                    user_name = teams_info.get("name", user_name)
                    email = teams_info.get("email", "")
                except Exception as e:
                    logger.warning(f"Could not get Teams user info: {e}")
                    email = ""
            else:
                email = ""
            
            # Create basic claims structure
            claims = {
                "oid": user_id,
                "name": user_name,
                "email": email,
                "tenant_id": self.config.tenant_id,
                "groups": [],  # Will be populated if needed
                "roles": [],   # Will be populated if needed
                "channel_id": turn_context.activity.channel_id,
                "conversation_id": turn_context.activity.conversation.id
            }
            
            return claims
            
        except Exception as e:
            logger.error(f"Error getting user claims: {e}")
            # Return minimal claims on error
            return {
                "oid": turn_context.activity.from_property.id,
                "name": "Unknown User",
                "email": "",
                "tenant_id": self.config.tenant_id,
                "groups": [],
                "roles": [],
                "channel_id": turn_context.activity.channel_id,
                "conversation_id": turn_context.activity.conversation.id
            }
    
    async def _get_teams_user_info(self, turn_context: TurnContext) -> Dict[str, Any]:
        """Get Teams-specific user information."""
        try:
            # This would typically use TeamsInfo to get user details
            # For now, we'll return basic information
            return {
                "name": turn_context.activity.from_property.name or "Unknown User",
                "email": "",
                "id": turn_context.activity.from_property.id
            }
        except Exception as e:
            logger.warning(f"Could not get Teams user info: {e}")
            return {
                "name": "Unknown User",
                "email": "",
                "id": turn_context.activity.from_property.id
            }
    
    async def validate_user_access(self, user_claims: Dict[str, Any], resource: str) -> bool:
        """
        Validate if a user has access to a specific resource.
        This method integrates with existing access control logic.
        """
        try:
            # For now, we'll implement basic access control
            # In the next phase, we'll integrate with the existing authentication system
            
            # Check if user is authenticated
            if not user_claims.get("oid"):
                return False
            
            # Check if user belongs to the correct tenant
            if user_claims.get("tenant_id") != self.config.tenant_id:
                return False
            
            # Additional access control logic can be added here
            # For example, checking groups, roles, or specific permissions
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating user access: {e}")
            return False
    
    async def get_user_groups(self, user_claims: Dict[str, Any]) -> list[str]:
        """
        Get user groups for access control.
        This method can be extended to integrate with Microsoft Graph.
        """
        try:
            # For now, return empty list
            # In the next phase, we'll integrate with Microsoft Graph to get actual groups
            return user_claims.get("groups", [])
            
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []
    
    async def get_user_roles(self, user_claims: Dict[str, Any]) -> list[str]:
        """
        Get user roles for access control.
        This method can be extended to integrate with Microsoft Graph.
        """
        try:
            # For now, return empty list
            # In the next phase, we'll integrate with Microsoft Graph to get actual roles
            return user_claims.get("roles", [])
            
        except Exception as e:
            logger.error(f"Error getting user roles: {e}")
            return []
    
    async def get_access_token(self, scopes: Optional[List[str]] = None) -> Optional[str]:
        """
        Get an access token for Microsoft Graph API calls.
        """
        try:
            if scopes is None:
                scopes = ["https://graph.microsoft.com/.default"]
            
            if not self._msal_app:
                logger.error("MSAL app not initialized")
                return None
            
            result = self._msal_app.acquire_token_for_client(scopes=scopes)
            
            if "access_token" in result:
                return result["access_token"]
            else:
                logger.error(f"Failed to acquire token: {result.get('error_description')}")
                return None
                
        except Exception as e:
            logger.error(f"Error acquiring access token: {e}")
            return None
    
    async def get_user_from_graph(self, user_id: str, access_token: str) -> Optional[GraphUserInfo]:
        """
        Get user information from Microsoft Graph.
        """
        try:
            if not self._http_session:
                logger.error("HTTP session not initialized")
                return None
            
            url = f"{self._graph_base_url}/users/{user_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with self._http_session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return GraphUserInfo(
                        id=data.get("id", ""),
                        display_name=data.get("displayName", ""),
                        mail=data.get("mail", ""),
                        user_principal_name=data.get("userPrincipalName", ""),
                        job_title=data.get("jobTitle"),
                        department=data.get("department"),
                        office_location=data.get("officeLocation"),
                        mobile_phone=data.get("mobilePhone"),
                        business_phones=data.get("businessPhones", []),
                        preferred_language=data.get("preferredLanguage")
                    )
                else:
                    logger.error(f"Failed to get user from Graph: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting user from Graph: {e}")
            return None
    
    async def get_user_groups_from_graph(self, user_id: str, access_token: str) -> List[GraphGroupInfo]:
        """
        Get user groups from Microsoft Graph.
        """
        try:
            if not self._http_session:
                logger.error("HTTP session not initialized")
                return []
            
            url = f"{self._graph_base_url}/users/{user_id}/memberOf"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            groups = []
            async with self._http_session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("value", []):
                        if item.get("@odata.type") == "#microsoft.graph.group":
                            groups.append(GraphGroupInfo(
                                id=item.get("id", ""),
                                display_name=item.get("displayName", ""),
                                description=item.get("description"),
                                group_types=item.get("groupTypes", []),
                                security_enabled=item.get("securityEnabled", False)
                            ))
                else:
                    logger.error(f"Failed to get user groups from Graph: {response.status}")
            
            return groups
            
        except Exception as e:
            logger.error(f"Error getting user groups from Graph: {e}")
            return []
    
    async def get_user_roles_from_graph(self, user_id: str, access_token: str) -> List[str]:
        """
        Get user roles from Microsoft Graph (Azure AD roles).
        """
        try:
            if not self._http_session:
                logger.error("HTTP session not initialized")
                return []
            
            url = f"{self._graph_base_url}/users/{user_id}/memberOf"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            roles = []
            async with self._http_session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("value", []):
                        if item.get("@odata.type") == "#microsoft.graph.directoryRole":
                            roles.append(item.get("displayName", ""))
                else:
                    logger.error(f"Failed to get user roles from Graph: {response.status}")
            
            return roles
            
        except Exception as e:
            logger.error(f"Error getting user roles from Graph: {e}")
            return []
    
    async def validate_token(self, token: str) -> bool:
        """
        Validate a user token using Microsoft Graph.
        """
        try:
            if not self._http_session:
                logger.error("HTTP session not initialized")
                return False
            
            url = f"{self._graph_base_url}/me"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with self._http_session.get(url, headers=headers) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False
    
    async def get_enhanced_user_claims(self, turn_context: TurnContext) -> UserClaims:
        """
        Get enhanced user claims with Microsoft Graph data.
        """
        try:
            # Get basic claims first
            basic_claims = await self.get_user_claims(turn_context)
            user_id = basic_claims.get("oid", "")
            
            # Check cache first
            if user_id in self._token_cache:
                cached_claims = self._token_cache[user_id]
                if cached_claims.last_updated and (datetime.now() - cached_claims.last_updated).seconds < 300:  # 5 minutes
                    return cached_claims
            
            # Get access token for Graph calls
            access_token = await self.get_access_token()
            if not access_token:
                logger.warning("Could not get access token for Graph calls")
                return UserClaims(
                    user_id=user_id,
                    user_name=basic_claims.get("name", "Unknown User"),
                    email=basic_claims.get("email", ""),
                    tenant_id=basic_claims.get("tenant_id", ""),
                    groups=[],
                    roles=[],
                    additional_claims=basic_claims,
                    is_authenticated=False
                )
            
            # Get user info from Graph
            graph_user = await self.get_user_from_graph(user_id, access_token)
            if graph_user:
                # Get groups and roles
                groups = await self.get_user_groups_from_graph(user_id, access_token)
                roles = await self.get_user_roles_from_graph(user_id, access_token)
                
                # Create enhanced claims
                enhanced_claims = UserClaims(
                    user_id=user_id,
                    user_name=graph_user.display_name,
                    email=graph_user.mail or graph_user.user_principal_name,
                    tenant_id=basic_claims.get("tenant_id", ""),
                    groups=[group.display_name for group in groups],
                    roles=roles,
                    additional_claims={
                        **basic_claims,
                        "graph_user": {
                            "job_title": graph_user.job_title,
                            "department": graph_user.department,
                            "office_location": graph_user.office_location,
                            "mobile_phone": graph_user.mobile_phone,
                            "business_phones": graph_user.business_phones,
                            "preferred_language": graph_user.preferred_language
                        },
                        "graph_groups": [
                            {
                                "id": group.id,
                                "display_name": group.display_name,
                                "description": group.description,
                                "security_enabled": group.security_enabled
                            }
                            for group in groups
                        ]
                    },
                    access_token=access_token,
                    is_authenticated=True,
                    last_updated=datetime.now()
                )
                
                # Cache the claims
                self._token_cache[user_id] = enhanced_claims
                
                return enhanced_claims
            else:
                # Fallback to basic claims
                return UserClaims(
                    user_id=user_id,
                    user_name=basic_claims.get("name", "Unknown User"),
                    email=basic_claims.get("email", ""),
                    tenant_id=basic_claims.get("tenant_id", ""),
                    groups=[],
                    roles=[],
                    additional_claims=basic_claims,
                    is_authenticated=False
                )
                
        except Exception as e:
            logger.error(f"Error getting enhanced user claims: {e}")
            # Return basic claims on error
            basic_claims = await self.get_user_claims(turn_context)
            return UserClaims(
                user_id=basic_claims.get("oid", ""),
                user_name=basic_claims.get("name", "Unknown User"),
                email=basic_claims.get("email", ""),
                tenant_id=basic_claims.get("tenant_id", ""),
                groups=[],
                roles=[],
                additional_claims=basic_claims,
                is_authenticated=False
            )
    
    async def check_user_permission(self, user_claims: UserClaims, permission: str) -> bool:
        """
        Check if user has a specific permission based on groups and roles.
        """
        try:
            # Define permission mappings
            permission_mappings = {
                "read_documents": ["Document Readers", "All Users"],
                "write_documents": ["Document Writers", "Document Administrators"],
                "admin_access": ["Document Administrators", "Global Administrators"],
                "structural_analysis": ["Structural Engineers", "Document Readers"],
                "code_review": ["Code Reviewers", "Document Writers"],
                "system_admin": ["Global Administrators", "System Administrators"]
            }
            
            required_groups = permission_mappings.get(permission, [])
            if not required_groups:
                logger.warning(f"Unknown permission: {permission}")
                return False
            
            # Check if user is in any of the required groups
            user_groups = user_claims.groups
            user_roles = user_claims.roles
            
            # Check groups
            for group in user_groups:
                if group in required_groups:
                    return True
            
            # Check roles
            for role in user_roles:
                if role in required_groups:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking user permission: {e}")
            return False
    
    async def close(self) -> None:
        """Close the authentication service and clean up resources."""
        try:
            if self._credential:
                await self._credential.close()
            
            if self._http_session:
                await self._http_session.close()
            
            # Clear token cache
            self._token_cache.clear()
            
            logger.info("Auth Service closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing Auth Service: {e}")