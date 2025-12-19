"""
Authentication module for OAuth2/SAML support.

This module provides:
- Azure AD OAuth2 integration
- JWT token management
- Role-Based Access Control (RBAC)
"""

from .azure_ad import AzureADAuth, require_auth
from .jwt_handler import JWTHandler

__all__ = [
    "AzureADAuth",
    "require_auth",
    "JWTHandler",
]
