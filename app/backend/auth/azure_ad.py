"""
Azure Active Directory OAuth2 integration.

This module handles Azure AD OAuth2 flows and token validation.
Supports Azure AD multi-tenant applications.
"""

import os
import logging
from typing import Optional, Dict
from functools import wraps
from datetime import datetime

import aiohttp
import jwt
from quart import request, jsonify

logger = logging.getLogger(__name__)


class AzureADAuth:
    """
    Azure Active Directory OAuth2 authentication handler.
    
    Attributes:
        tenant_id: Azure AD tenant ID
        client_id: Azure AD application ID
        jwks_url: URL to fetch JSON Web Key Set from Azure AD
        authority_url: Azure AD authority endpoint
    """

    def __init__(
        self,
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
    ):
        """
        Initialize Azure AD auth handler.
        
        Args:
            tenant_id: Azure AD tenant ID (defaults to env AZURE_TENANT_ID)
            client_id: Azure AD app ID (defaults to env AZURE_CLIENT_ID)
            client_secret: Azure AD app secret (defaults to env AZURE_CLIENT_SECRET)
        """
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
        
        if not self.tenant_id or not self.client_id:
            logger.warning(
                "Azure AD configuration incomplete. "
                "Set AZURE_TENANT_ID and AZURE_CLIENT_ID environment variables."
            )
        
        self.authority_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}"
        )
        self.jwks_url = f"{self.authority_url}/discovery/v2.0/keys"
        self._jwks_cache: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None

    async def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token from Azure AD.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Token payload dict if valid, None otherwise
        """
        try:
            # Decode header without verification to get 'kid'
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid:
                logger.warning("Token missing 'kid' in header")
                return None
            
            # Get JWKS from Azure AD
            keys = await self._get_jwks()
            if not keys:
                logger.error("Failed to fetch JWKS from Azure AD")
                return None
            
            # Find matching public key
            public_key = self._find_key(keys, kid)
            if not public_key:
                logger.warning(f"Public key with kid '{kid}' not found")
                return None
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"{self.authority_url}/v2.0",
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token has expired")
            return None
        except jwt.InvalidAudienceError:
            logger.warning("Token audience mismatch")
            return None
        except jwt.InvalidIssuerError:
            logger.warning("Token issuer mismatch")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return None

    async def _get_jwks(self) -> Optional[Dict]:
        """
        Fetch JSON Web Key Set from Azure AD.
        
        Caches result for 1 hour to reduce API calls.
        
        Returns:
            JWKS dict or None if fetch fails
        """
        # Check cache (valid for 1 hour)
        if self._jwks_cache and self._cache_timestamp:
            time_diff = (datetime.utcnow() - self._cache_timestamp).total_seconds()
            if time_diff < 3600:  # 1 hour
                return self._jwks_cache
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.jwks_url,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        self._jwks_cache = await response.json()
                        self._cache_timestamp = datetime.utcnow()
                        return self._jwks_cache
                    else:
                        logger.error(
                            f"Failed to fetch JWKS: HTTP {response.status}"
                        )
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching JWKS: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching JWKS: {e}")
            return None

    @staticmethod
    def _find_key(keys: Dict, kid: str) -> Optional[str]:
        """
        Find public key from JWKS by kid.
        
        Args:
            keys: JWKS dict from Azure AD
            kid: Key ID to search for
            
        Returns:
            PEM-formatted public key or None
        """
        try:
            for key in keys.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM format
                    return jwt.algorithms.RSAAlgorithm.from_jwk(
                        key, as_additional_context=False
                    )
        except Exception as e:
            logger.error(f"Error converting JWK to PEM: {e}")
        
        return None

    async def get_token_endpoint(self) -> str:
        """Get Azure AD token endpoint URL."""
        return f"{self.authority_url}/oauth2/v2.0/token"

    async def get_authorize_endpoint(self) -> str:
        """Get Azure AD authorize endpoint URL."""
        return f"{self.authority_url}/oauth2/v2.0/authorize"


def require_auth(f):
    """
    Decorator for protected endpoints.
    
    Validates Bearer token in Authorization header.
    Adds auth_user to request context if valid.
    
    Returns 401 if token missing or invalid.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        try:
            # Get Authorization header
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header.startswith("Bearer "):
                logger.debug("Missing or invalid Authorization header")
                return jsonify({"error": "Missing Authorization header"}), 401
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Validate token with Azure AD
            auth = AzureADAuth()
            payload = await auth.validate_token(token)
            
            if not payload:
                logger.warning("Token validation failed")
                return jsonify({"error": "Invalid token"}), 401
            
            # Store in request context
            request.auth_user = payload
            
            # Call original function
            return await f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in auth decorator: {e}")
            return jsonify({"error": "Authentication error"}), 500
    
    return decorated_function
