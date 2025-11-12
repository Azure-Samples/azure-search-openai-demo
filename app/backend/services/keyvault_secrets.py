"""
Azure Key Vault Secrets Reader.

Provides utilities for reading secrets from Azure Key Vault using Managed Identity.
Falls back to environment variables if Key Vault is not configured or unavailable.
"""

import logging
import os
from typing import Optional, Dict, Any
from azure.identity.aio import ManagedIdentityCredential, DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


class KeyVaultSecretReader:
    """
    Reads secrets from Azure Key Vault with fallback to environment variables.
    
    Supports:
    - Managed Identity authentication (when running on Azure)
    - DefaultAzureCredential (for local development)
    - Environment variable fallback
    """
    
    def __init__(
        self,
        key_vault_url: Optional[str] = None,
        credential: Optional[Any] = None,
        enable_keyvault: bool = True
    ):
        """
        Initialize Key Vault secret reader.
        
        Args:
            key_vault_url: Key Vault URL (e.g., https://myvault.vault.azure.net/)
            credential: Azure credential (ManagedIdentityCredential, DefaultAzureCredential, etc.)
            enable_keyvault: Whether to attempt Key Vault reads (default: True)
        """
        self.key_vault_url = key_vault_url or os.getenv("AZURE_KEY_VAULT_ENDPOINT")
        self.credential = credential
        self.enable_keyvault = enable_keyvault and self.key_vault_url is not None
        self._client: Optional[SecretClient] = None
        self._cache: Dict[str, Any] = {}
    
    async def _get_client(self) -> Optional[SecretClient]:
        """Get or create Key Vault client."""
        if not self.enable_keyvault:
            return None
        
        if self._client is None:
            try:
                if self.credential is None:
                    # Try Managed Identity first (for Azure), then DefaultAzureCredential
                    try:
                        self.credential = ManagedIdentityCredential()
                    except Exception:
                        self.credential = DefaultAzureCredential()
                
                self._client = SecretClient(
                    vault_url=self.key_vault_url,
                    credential=self.credential
                )
                logger.info(f"Key Vault client initialized for: {self.key_vault_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize Key Vault client: {e}. Will use environment variables.")
                self.enable_keyvault = False
                return None
        
        return self._client
    
    async def get_secret(
        self,
        secret_name: str,
        env_var_name: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Get secret from Key Vault or environment variable.
        
        Priority:
        1. Key Vault (if enabled and available)
        2. Environment variable (if env_var_name provided)
        3. None
        
        Args:
            secret_name: Name of the secret in Key Vault
            env_var_name: Optional environment variable name (if different from secret_name)
            use_cache: Whether to cache the secret value (default: True)
            
        Returns:
            Secret value or None if not found
        """
        # Check cache first
        cache_key = secret_name
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try Key Vault first
        if self.enable_keyvault:
            try:
                client = await self._get_client()
                if client:
                    secret = await client.get_secret(secret_name)
                    value = secret.value
                    
                    # Cache the value
                    if use_cache:
                        self._cache[cache_key] = value
                    
                    logger.debug(f"Retrieved secret '{secret_name}' from Key Vault")
                    return value
            except AzureError as e:
                logger.warning(f"Failed to get secret '{secret_name}' from Key Vault: {e}. Falling back to environment variable.")
            except Exception as e:
                logger.warning(f"Unexpected error getting secret '{secret_name}' from Key Vault: {e}. Falling back to environment variable.")
        
        # Fallback to environment variable
        env_name = env_var_name or secret_name
        value = os.getenv(env_name)
        
        if value:
            logger.debug(f"Retrieved secret '{secret_name}' from environment variable '{env_name}'")
            if use_cache:
                self._cache[cache_key] = value
            return value
        
        logger.debug(f"Secret '{secret_name}' not found in Key Vault or environment variable '{env_name}'")
        return None
    
    async def get_secrets(
        self,
        secret_mappings: Dict[str, Optional[str]]
    ) -> Dict[str, Optional[str]]:
        """
        Get multiple secrets from Key Vault or environment variables.
        
        Args:
            secret_mappings: Dictionary mapping secret names to optional env var names
                           e.g., {"MICROSOFT_APP_PASSWORD": "MICROSOFT_APP_PASSWORD",
                                  "AZURE_SEARCH_KEY": "AZURE_SEARCH_KEY"}
        
        Returns:
            Dictionary with secret values (None if not found)
        """
        results = {}
        for secret_name, env_var_name in secret_mappings.items():
            results[secret_name] = await self.get_secret(secret_name, env_var_name)
        return results
    
    async def close(self):
        """Close the Key Vault client and clean up resources."""
        if self._client:
            await self._client.close()
            self._client = None
        if self.credential and hasattr(self.credential, 'close'):
            await self.credential.close()
        self._cache.clear()





