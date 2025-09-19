"""
Authentication Service for Microsoft 365 Agent.
This service handles authentication and authorization for the agent.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from botbuilder.core import TurnContext
from azure.identity.aio import DefaultAzureCredential
from msal import ConfidentialClientApplication

from config.agent_config import AgentConfig


logger = logging.getLogger(__name__)


@dataclass
class UserClaims:
    """User claims from Microsoft 365 authentication."""
    user_id: str
    user_name: str
    email: str
    tenant_id: str
    groups: list[str]
    roles: list[str]
    additional_claims: Dict[str, Any]


class AuthService:
    """
    Authentication Service that handles Microsoft 365 authentication and authorization.
    Integrates with existing authentication system while providing agent-specific functionality.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self._credential = DefaultAzureCredential()
        self._msal_app: Optional[ConfidentialClientApplication] = None
    
    async def initialize(self) -> None:
        """Initialize the authentication service."""
        try:
            # Initialize MSAL application for token validation
            self._msal_app = ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=f"https://login.microsoftonline.com/{self.config.tenant_id}"
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
    
    async def close(self) -> None:
        """Close the authentication service and clean up resources."""
        if self._credential:
            await self._credential.close()