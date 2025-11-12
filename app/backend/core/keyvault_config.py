"""
Key Vault Configuration Helper.

Provides a centralized way to load configuration from Key Vault or environment variables.
"""

import logging
import os
from typing import Optional, Dict, Any
from services.keyvault_secrets import KeyVaultSecretReader

logger = logging.getLogger(__name__)


class KeyVaultConfigLoader:
    """
    Loads application configuration from Key Vault with environment variable fallback.
    
    This is a convenience wrapper around KeyVaultSecretReader that provides
    application-specific secret loading.
    """
    
    def __init__(self, key_vault_url: Optional[str] = None, credential: Optional[Any] = None):
        """
        Initialize config loader.
        
        Args:
            key_vault_url: Key Vault URL (optional, will use AZURE_KEY_VAULT_ENDPOINT env var)
            credential: Azure credential (optional)
        """
        self.reader = KeyVaultSecretReader(
            key_vault_url=key_vault_url,
            credential=credential,
            enable_keyvault=True
        )
    
    async def load_bot_secrets(self) -> Dict[str, Optional[str]]:
        """
        Load Bot Framework secrets from Key Vault.
        
        Returns:
            Dictionary with MICROSOFT_APP_ID and MICROSOFT_APP_PASSWORD
        """
        return await self.reader.get_secrets({
            "MICROSOFT_APP_ID": "MICROSOFT_APP_ID",
            "MICROSOFT_APP_PASSWORD": "MICROSOFT_APP_PASSWORD"
        })
    
    async def load_azure_secrets(self) -> Dict[str, Optional[str]]:
        """
        Load Azure service secrets from Key Vault.
        
        Returns:
            Dictionary with Azure service keys
        """
        return await self.reader.get_secrets({
            "AZURE_SEARCH_KEY": "AZURE_SEARCH_KEY",
            "AZURE_OPENAI_API_KEY": "AZURE_OPENAI_API_KEY",
            "AZURE_CLIENT_SECRET": "AZURE_CLIENT_SECRET",
            "AZURE_DOCUMENT_INTELLIGENCE_KEY": "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        })
    
    async def load_web_search_secrets(self) -> Dict[str, Optional[str]]:
        """
        Load web search provider secrets from Key Vault.
        
        Returns:
            Dictionary with web search API keys
        """
        return await self.reader.get_secrets({
            "SERPER_API_KEY": "SERPER_API_KEY",
            "DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY"
        })
    
    async def load_all_secrets(self) -> Dict[str, Optional[str]]:
        """
        Load all application secrets from Key Vault.
        
        Returns:
            Dictionary with all secrets
        """
        bot_secrets = await self.load_bot_secrets()
        azure_secrets = await self.load_azure_secrets()
        web_secrets = await self.load_web_search_secrets()
        
        return {**bot_secrets, **azure_secrets, **web_secrets}
    
    async def close(self):
        """Close the Key Vault reader."""
        await self.reader.close()


async def get_secret_from_keyvault_or_env(
    secret_name: str,
    env_var_name: Optional[str] = None,
    key_vault_url: Optional[str] = None,
    credential: Optional[Any] = None
) -> Optional[str]:
    """
    Convenience function to get a secret from Key Vault or environment variable.
    
    Args:
        secret_name: Name of the secret in Key Vault
        env_var_name: Optional environment variable name (defaults to secret_name)
        key_vault_url: Optional Key Vault URL (uses AZURE_KEY_VAULT_ENDPOINT if not provided)
        credential: Optional Azure credential
        
    Returns:
        Secret value or None if not found
    """
    reader = KeyVaultSecretReader(key_vault_url=key_vault_url, credential=credential)
    try:
        return await reader.get_secret(secret_name, env_var_name)
    finally:
        await reader.close()

