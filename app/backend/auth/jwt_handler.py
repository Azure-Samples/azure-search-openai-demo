"""
JWT token generation and validation.

Handles creation of access and refresh tokens with standard claims.
Uses HS256 (HMAC) for signing.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

import jwt

logger = logging.getLogger(__name__)


class JWTHandler:
    """
    JWT token handler for access and refresh tokens.
    
    Attributes:
        secret: Secret key for signing tokens
        algorithm: Algorithm for signing (HS256)
        access_token_expire: Minutes until access token expires (default 15)
        refresh_token_expire: Days until refresh token expires (default 7)
    """

    def __init__(
        self,
        secret: str = None,
        algorithm: str = "HS256",
        access_token_expire: int = 15,
        refresh_token_expire: int = 7,
    ):
        """
        Initialize JWT handler.
        
        Args:
            secret: Secret key for signing (defaults to JWT_SECRET_KEY env var)
            algorithm: Signing algorithm (default HS256)
            access_token_expire: Minutes until access token expires (default 15)
            refresh_token_expire: Days until refresh token expires (default 7)
            
        Raises:
            ValueError: If secret not provided and JWT_SECRET_KEY not in env
        """
        self.secret = secret or os.getenv("JWT_SECRET_KEY")
        if not self.secret:
            raise ValueError(
                "JWT_SECRET_KEY must be provided or set in environment"
            )
        
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire
        self.refresh_token_expire = refresh_token_expire

    def create_tokens(
        self,
        user_id: str,
        user_email: str,
        roles: List[str] = None,
        additional_claims: Dict = None,
    ) -> Dict[str, str]:
        """
        Generate access and refresh tokens.
        
        Args:
            user_id: Unique user identifier
            user_email: User email address
            roles: List of user roles (default ['user'])
            additional_claims: Extra claims to include in token
            
        Returns:
            Dict with access_token, refresh_token, token_type, expires_in
        """
        roles = roles or ["user"]
        additional_claims = additional_claims or {}
        
        try:
            now = datetime.utcnow()
            
            # Access token payload
            access_payload = {
                "sub": user_id,
                "email": user_email,
                "roles": roles,
                "type": "access",
                "exp": now + timedelta(minutes=self.access_token_expire),
                "iat": now,
                "nbf": now,
            }
            access_payload.update(additional_claims)
            
            access_token = jwt.encode(
                access_payload,
                self.secret,
                algorithm=self.algorithm,
            )
            
            # Refresh token payload
            refresh_payload = {
                "sub": user_id,
                "type": "refresh",
                "exp": now + timedelta(days=self.refresh_token_expire),
                "iat": now,
                "nbf": now,
            }
            
            refresh_token = jwt.encode(
                refresh_payload,
                self.secret,
                algorithm=self.algorithm,
            )
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": self.access_token_expire * 60,  # Convert to seconds
            }
            
        except Exception as e:
            logger.error(f"Error creating tokens: {e}")
            raise

    def validate_token(
        self,
        token: str,
        token_type: str = "access",
    ) -> Optional[Dict]:
        """
        Validate and decode token.
        
        Args:
            token: JWT token to validate
            token_type: Expected token type ('access' or 'refresh')
            
        Returns:
            Token payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                logger.warning(
                    f"Token type mismatch: expected {token_type}, "
                    f"got {payload.get('type')}"
                )
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token or None if refresh_token invalid
        """
        try:
            # Validate refresh token
            payload = self.validate_token(refresh_token, token_type="refresh")
            if not payload:
                logger.warning("Refresh token validation failed")
                return None
            
            user_id = payload.get("sub")
            email = payload.get("email", "")
            roles = payload.get("roles", ["user"])
            
            # Create new access token
            now = datetime.utcnow()
            access_payload = {
                "sub": user_id,
                "email": email,
                "roles": roles,
                "type": "access",
                "exp": now + timedelta(minutes=self.access_token_expire),
                "iat": now,
                "nbf": now,
            }
            
            access_token = jwt.encode(
                access_payload,
                self.secret,
                algorithm=self.algorithm,
            )
            
            return access_token
            
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    def decode_token(self, token: str, verify: bool = True) -> Optional[Dict]:
        """
        Decode token without verification (for debugging).
        
        Args:
            token: JWT token to decode
            verify: If False, don't verify signature
            
        Returns:
            Token payload dict or None
        """
        try:
            if verify:
                return self.validate_token(token)
            else:
                return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            return None

    def get_token_claims(self, token: str) -> Optional[Dict]:
        """
        Get decoded token claims without validation.
        
        Useful for debugging and logging.
        
        Args:
            token: JWT token
            
        Returns:
            Token claims dict or None
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False},
            )
        except Exception as e:
            logger.error(f"Error getting token claims: {e}")
            return None
