"""
Validaciones específicas de RBAC para Azure Search
"""
import os
import logging
import aiohttp
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError

logger = logging.getLogger("rbac_validation")

# Roles necesarios para Azure Search
REQUIRED_SEARCH_ROLES = [
    "1407120a-92aa-4202-b7e9-c0e197c71c8f",  # Search Index Data Reader
    "8ebe5a00-799e-43f5-93ac-243d3dce84a7",  # Search Index Data Contributor
    "7ca78c08-252a-4471-8644-bb5ff32d4ba0",  # Search Service Contributor
]

ROLE_NAMES = {
    "1407120a-92aa-4202-b7e9-c0e197c71c8f": "Search Index Data Reader",
    "8ebe5a00-799e-43f5-93ac-243d3dce84a7": "Search Index Data Contributor", 
    "7ca78c08-252a-4471-8644-bb5ff32d4ba0": "Search Service Contributor",
}

async def get_managed_identity_principal_id(credential) -> str:
    """
    Obtiene el Principal ID del Managed Identity actual
    """
    try:
        # Obtener token para management API
        token = await credential.get_token("https://management.azure.com/.default")
        if not token:
            return None
            
        # Usar Instance Metadata Service para obtener info del MI
        metadata_url = "http://169.254.169.254/metadata/identity/oauth2/token"
        params = {
            "api-version": "2018-02-01",
            "resource": "https://management.azure.com/"
        }
        headers = {"Metadata": "true"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(metadata_url, params=params, headers=headers, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    # El token JWT contiene el principal ID en el claim 'oid'
                    import base64
                    import json
                    
                    # Decodificar token JWT (solo payload, sin verificar firma)
                    token_parts = data.get("access_token", "").split(".")
                    if len(token_parts) >= 2:
                        # Decodificar payload (base64)
                        payload = token_parts[1]
                        # Agregar padding si es necesario
                        payload += "=" * (4 - len(payload) % 4)
                        decoded = base64.b64decode(payload)
                        token_data = json.loads(decoded)
                        return token_data.get("oid")
                        
    except Exception as e:
        logger.warning(f"No se pudo obtener Principal ID: {str(e)}")
        return None

async def validate_rbac_assignments(
    subscription_id: str,
    resource_group: str, 
    search_service_name: str,
    credential
) -> dict:
    """
    Valida que el Managed Identity tenga los roles RBAC necesarios para Azure Search
    
    Returns:
        dict: Resultado detallado de la validación RBAC
    """
    logger.info("🔐 Iniciando validación explícita de RBAC...")
    
    result = {
        "success": False,
        "principal_id": None,
        "required_roles": ROLE_NAMES.copy(),
        "assigned_roles": [],
        "missing_roles": [],
        "scope": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Search/searchServices/{search_service_name}",
        "errors": []
    }
    
    try:
        # 1. Obtener Principal ID del Managed Identity
        logger.info("📋 Obteniendo Principal ID del Managed Identity...")
        principal_id = await get_managed_identity_principal_id(credential)
        
        if not principal_id:
            result["errors"].append("No se pudo obtener Principal ID del Managed Identity")
            return result
            
        result["principal_id"] = principal_id
        logger.info(f"✅ Principal ID: {principal_id}")
        
        # 2. Obtener token para Management API
        token = await credential.get_token("https://management.azure.com/.default")
        if not token:
            result["errors"].append("No se pudo obtener token para Management API")
            return result
            
        # 3. Consultar role assignments en el scope del Search Service
        scope = result["scope"]
        assignments_url = f"https://management.azure.com{scope}/providers/Microsoft.Authorization/roleAssignments"
        
        params = {
            "api-version": "2022-04-01",
            "$filter": f"principalId eq '{principal_id}'"
        }
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"🔍 Consultando role assignments en: {scope}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(assignments_url, params=params, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    assignments = data.get("value", [])
                    
                    # Analizar assignments encontrados
                    assigned_role_ids = []
                    for assignment in assignments:
                        properties = assignment.get("properties", {})
                        role_definition_id = properties.get("roleDefinitionId", "")
                        # Extraer solo el GUID del role
                        if "/" in role_definition_id:
                            role_id = role_definition_id.split("/")[-1]
                            assigned_role_ids.append(role_id)
                            
                    result["assigned_roles"] = [
                        {"id": role_id, "name": ROLE_NAMES.get(role_id, f"Unknown ({role_id})")}
                        for role_id in assigned_role_ids
                    ]
                    
                    # Verificar roles requeridos vs asignados
                    missing_role_ids = set(REQUIRED_SEARCH_ROLES) - set(assigned_role_ids)
                    result["missing_roles"] = [
                        {"id": role_id, "name": ROLE_NAMES[role_id]}
                        for role_id in missing_role_ids
                    ]
                    
                    # Evaluar resultado
                    if not missing_role_ids:
                        result["success"] = True
                        logger.info("✅ Todos los roles RBAC requeridos están asignados")
                    else:
                        logger.error(f"❌ Faltan {len(missing_role_ids)} roles RBAC requeridos")
                        for missing in result["missing_roles"]:
                            logger.error(f"   - {missing['name']} ({missing['id']})")
                            
                elif response.status == 403:
                    result["errors"].append("Sin permisos para consultar role assignments")
                    logger.warning("⚠️ No se pudo verificar RBAC - sin permisos para Management API")
                else:
                    error_text = await response.text()
                    result["errors"].append(f"Error HTTP {response.status}: {error_text}")
                    
    except Exception as e:
        error_msg = f"Error durante validación RBAC: {str(e)}"
        result["errors"].append(error_msg)
        logger.error(f"❌ {error_msg}")
        
    return result

async def validate_rbac_for_search() -> bool:
    """
    Punto de entrada principal para validación RBAC de Azure Search
    """
    # Obtener configuración del environment
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_SEARCH_SERVICE_RESOURCE_GROUP")
    search_service = os.getenv("AZURE_SEARCH_SERVICE")
    
    if not all([subscription_id, resource_group, search_service]):
        logger.error("❌ Faltan variables de entorno para validación RBAC:")
        logger.error(f"   AZURE_SUBSCRIPTION_ID: {subscription_id}")
        logger.error(f"   AZURE_SEARCH_SERVICE_RESOURCE_GROUP: {resource_group}")
        logger.error(f"   AZURE_SEARCH_SERVICE: {search_service}")
        return False
    
    # Crear credencial
    credential = DefaultAzureCredential()
    
    try:
        # Ejecutar validación
        result = await validate_rbac_assignments(
            subscription_id=subscription_id,
            resource_group=resource_group,
            search_service_name=search_service,
            credential=credential
        )
        
        # Reportar resultados detallados
        logger.info("📊 === REPORTE DE VALIDACIÓN RBAC ===")
        logger.info(f"🎯 Scope: {result['scope']}")
        logger.info(f"👤 Principal ID: {result['principal_id']}")
        logger.info(f"✅ Roles asignados: {len(result['assigned_roles'])}")
        
        for role in result["assigned_roles"]:
            logger.info(f"   ✓ {role['name']}")
            
        if result["missing_roles"]:
            logger.info(f"❌ Roles faltantes: {len(result['missing_roles'])}")
            for role in result["missing_roles"]:
                logger.info(f"   ✗ {role['name']}")
                
        if result["errors"]:
            logger.info(f"⚠️ Errores: {len(result['errors'])}")
            for error in result["errors"]:
                logger.info(f"   ! {error}")
                
        return result["success"]
        
    finally:
        await credential.close()

# Función helper para usar en debug endpoints
async def get_rbac_status_dict() -> dict:
    """
    Obtiene el estado RBAC como diccionario para endpoints de debug
    """
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_SEARCH_SERVICE_RESOURCE_GROUP")
    search_service = os.getenv("AZURE_SEARCH_SERVICE")
    
    if not all([subscription_id, resource_group, search_service]):
        return {
            "rbac_validation": "error",
            "error": "Missing environment variables for RBAC validation"
        }
    
    credential = DefaultAzureCredential()
    
    try:
        result = await validate_rbac_assignments(
            subscription_id=subscription_id,
            resource_group=resource_group,
            search_service_name=search_service,
            credential=credential
        )
        
        return {
            "rbac_validation": "success" if result["success"] else "failed",
            "principal_id": result["principal_id"],
            "scope": result["scope"],
            "assigned_roles": result["assigned_roles"],
            "missing_roles": result["missing_roles"],
            "errors": result["errors"]
        }
        
    except Exception as e:
        return {
            "rbac_validation": "error",
            "error": str(e)
        }
    finally:
        await credential.close()
