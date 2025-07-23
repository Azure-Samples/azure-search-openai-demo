"""
Azure Credential Provider
Proporciona la credencial correcta según el entorno de ejecución.
"""
import os
import logging
from typing import Union
from azure.identity import ManagedIdentityCredential, ClientSecretCredential
from azure.identity.aio import ManagedIdentityCredential as AsyncManagedIdentityCredential, ClientSecretCredential as AsyncClientSecretCredential

logger = logging.getLogger(__name__)

def get_azure_credential() -> Union[ManagedIdentityCredential, ClientSecretCredential]:
    """
    Obtiene la credencial correcta para autenticación con Azure.
    
    Returns:
        - ClientSecretCredential para desarrollo local (env=dev)
        - ManagedIdentityCredential para producción en Azure
    """
    env = os.getenv("AZURE_ENV_NAME", "dev")
    running_in_production = os.getenv("RUNNING_IN_PRODUCTION", "").lower() == "true"
    website_hostname = os.getenv("WEBSITE_HOSTNAME")
    
    # Detectar si estamos en Azure (producción)
    is_azure_production = running_in_production or website_hostname is not None
    
    if is_azure_production:
        logger.info("🔐 Entorno: Azure (Producción) - Usando ManagedIdentityCredential")
        
        # Verificar si hay AZURE_CLIENT_ID para user-assigned managed identity
        azure_client_id = os.getenv("AZURE_CLIENT_ID")
        if azure_client_id:
            logger.info(f"🔧 Usando User-Assigned Managed Identity: {azure_client_id}")
            return ManagedIdentityCredential(client_id=azure_client_id)
        else:
            logger.info("🔧 Usando System-Assigned Managed Identity")
            return ManagedIdentityCredential()
    else:
        logger.info("🔐 Entorno: Desarrollo Local - Usando ClientSecretCredential")
        
        # Validar que tenemos todas las variables necesarias
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_APP_ID") 
        client_secret = os.getenv("AZURE_CLIENT_APP_SECRET")
        
        missing_vars = []
        if not tenant_id:
            missing_vars.append("AZURE_TENANT_ID")
        if not client_id:
            missing_vars.append("AZURE_CLIENT_APP_ID")
        if not client_secret:
            missing_vars.append("AZURE_CLIENT_APP_SECRET")
        
        if missing_vars:
            error_msg = f"❌ Variables de entorno faltantes para ClientSecretCredential: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"🔧 Usando ClientSecretCredential - Tenant: {tenant_id}, Client: {client_id}")
        
        try:
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            logger.info("✅ ClientSecretCredential creado exitosamente")
            return credential
        except Exception as e:
            error_msg = f"❌ Error creando ClientSecretCredential: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e


def get_azure_credential_async() -> Union[AsyncManagedIdentityCredential, AsyncClientSecretCredential]:
    """
    Versión asíncrona de get_azure_credential.
    
    Returns:
        - AsyncClientSecretCredential para desarrollo local
        - AsyncManagedIdentityCredential para producción en Azure
    """
    env = os.getenv("AZURE_ENV_NAME", "dev")
    running_in_production = os.getenv("RUNNING_IN_PRODUCTION", "").lower() == "true"
    website_hostname = os.getenv("WEBSITE_HOSTNAME")
    
    # Detectar si estamos en Azure (producción)
    is_azure_production = running_in_production or website_hostname is not None
    
    if is_azure_production:
        logger.info("🔐 Entorno: Azure (Producción) - Usando AsyncManagedIdentityCredential")
        
        # Verificar si hay AZURE_CLIENT_ID para user-assigned managed identity
        azure_client_id = os.getenv("AZURE_CLIENT_ID")
        if azure_client_id:
            logger.info(f"🔧 Usando User-Assigned Managed Identity (Async): {azure_client_id}")
            return AsyncManagedIdentityCredential(client_id=azure_client_id)
        else:
            logger.info("🔧 Usando System-Assigned Managed Identity (Async)")
            return AsyncManagedIdentityCredential()
    else:
        logger.info("🔐 Entorno: Desarrollo Local - Usando AsyncClientSecretCredential")
        
        # Validar que tenemos todas las variables necesarias
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_APP_ID") 
        client_secret = os.getenv("AZURE_CLIENT_APP_SECRET")
        
        missing_vars = []
        if not tenant_id:
            missing_vars.append("AZURE_TENANT_ID")
        if not client_id:
            missing_vars.append("AZURE_CLIENT_APP_ID")
        if not client_secret:
            missing_vars.append("AZURE_CLIENT_APP_SECRET")
        
        if missing_vars:
            error_msg = f"❌ Variables de entorno faltantes para AsyncClientSecretCredential: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"🔧 Usando AsyncClientSecretCredential - Tenant: {tenant_id}, Client: {client_id}")
        
        try:
            credential = AsyncClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            logger.info("✅ AsyncClientSecretCredential creado exitosamente")
            return credential
        except Exception as e:
            error_msg = f"❌ Error creando AsyncClientSecretCredential: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e


def validate_azure_credentials():
    """
    Valida que las credenciales de Azure estén correctamente configuradas.
    Útil para diagnóstico y debugging.
    """
    logger.info("🔍 Validando configuración de credenciales de Azure...")
    
    env_vars = {
        "AZURE_ENV_NAME": os.getenv("AZURE_ENV_NAME"),
        "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID"),
        "AZURE_CLIENT_APP_ID": os.getenv("AZURE_CLIENT_APP_ID"),
        "AZURE_CLIENT_APP_SECRET": "***" if os.getenv("AZURE_CLIENT_APP_SECRET") else None,
        "RUNNING_IN_PRODUCTION": os.getenv("RUNNING_IN_PRODUCTION"),
        "WEBSITE_HOSTNAME": os.getenv("WEBSITE_HOSTNAME"),
        "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID")
    }
    
    logger.info("📋 Variables de entorno relevantes:")
    for key, value in env_vars.items():
        if value:
            logger.info(f"  ✅ {key}: {value}")
        else:
            logger.warning(f"  ❌ {key}: No configurada")
    
    try:
        credential = get_azure_credential()
        logger.info(f"🎯 Tipo de credencial seleccionada: {type(credential).__name__}")
        return True
    except Exception as e:
        logger.error(f"💥 Error al obtener credencial: {str(e)}")
        return False


if __name__ == "__main__":
    # Para testing directo
    logging.basicConfig(level=logging.INFO)
    validate_azure_credentials()
