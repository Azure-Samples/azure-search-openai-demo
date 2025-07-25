"""
Healthchecks y validaciones para Azure Search
"""
import os
import logging
import asyncio
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from azure.search.documents.aio import SearchClient
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
import aiohttp


logger = logging.getLogger("search_health")


async def validate_search_access(endpoint: str, credential, index_name: str = None) -> bool:
    """
    Valida el acceso a Azure Search usando tanto la API REST como el SearchClient
    
    Args:
        endpoint: URL completa del servicio de Azure Search (ej: https://servicio.search.windows.net)
        credential: Credencial de Azure (DefaultAzureCredential o ManagedIdentityCredential)
        index_name: Nombre del índice para validar (opcional)
    
    Returns:
        bool: True si el acceso es exitoso, False en caso contrario
    """
    logger.info(f"🔍 Validando acceso a Azure Search: {endpoint}")
    
    # Validación 1: Verificar formato del endpoint
    if not endpoint.startswith("https://"):
        logger.error(f"❌ Endpoint debe usar HTTPS: {endpoint}")
        return False
    
    if not endpoint.endswith(".search.windows.net"):
        logger.error(f"❌ Endpoint no parece ser de Azure Search: {endpoint}")
        return False
    
    try:
        # Validación 2: Verificar que podemos obtener un token con el scope correcto
        logger.info("🔑 Obteniendo token para Azure Search...")
        token = await credential.get_token("https://search.azure.com/.default")
        
        if not token or not token.token:
            logger.error("❌ No se pudo obtener token para Azure Search")
            return False
        
        logger.info(f"✅ Token obtenido correctamente (expires: {token.expires_on})")
        logger.debug(f"Token preview: {token.token[:50]}...")
        
        # Validación 3: Probar acceso a la API REST de índices
        indexes_url = f"{endpoint}/indexes?api-version=2023-07-01-preview"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json"
            }
            
            logger.info("🌐 Probando acceso REST a /indexes...")
            async with session.get(indexes_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    indexes_data = await response.json()
                    indexes = indexes_data.get("value", [])
                    logger.info(f"✅ Acceso REST exitoso. {len(indexes)} índice(s) encontrado(s)")
                    
                    # Mostrar nombres de índices para debug
                    index_names = [idx.get("name", "sin_nombre") for idx in indexes]
                    logger.info(f"📋 Índices disponibles: {index_names}")
                    
                elif response.status == 403:
                    error_text = await response.text()
                    logger.error(f"❌ Error 403 (Forbidden) en REST API")
                    logger.error(f"Detalles: {error_text}")
                    return False
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Error HTTP {response.status} en REST API")
                    logger.error(f"Detalles: {error_text}")
                    return False
        
        # Validación 4: Si se proporciona index_name, probar SearchClient
        if index_name:
            logger.info(f"📖 Probando SearchClient con índice: {index_name}")
            
            search_client = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=credential
            )
            
            try:
                # Hacer una búsqueda simple para verificar acceso
                results = await search_client.search(search_text="*", top=1)
                count = 0
                async for result in results:
                    count += 1
                    break  # Solo necesitamos confirmar que funciona
                
                logger.info(f"✅ SearchClient funciona correctamente")
                await search_client.close()
                
            except Exception as e:
                logger.error(f"❌ Error con SearchClient: {str(e)}")
                await search_client.close()
                return False
        
        return True
        
    except ClientAuthenticationError as e:
        logger.error("❌ Error de autenticación con Managed Identity")
        logger.error("🔧 Verifica que el Container App tenga System-Assigned Managed Identity")
        logger.error("🔧 Verifica que el MI tenga los roles: Search Index Data Reader, Search Service Contributor")
        logger.debug(f"Detalles: {str(e)}")
        return False
        
    except HttpResponseError as e:
        logger.error(f"❌ Error HTTP al acceder a Azure Search: {e.status_code}")
        logger.error(f"Mensaje: {e.message}")
        
        if e.status_code == 403:
            logger.error("🔧 Error 403: Verifica permisos RBAC en Azure Search")
            logger.error("🔧 Roles necesarios: Search Index Data Reader, Search Service Contributor, Search Index Data Contributor")
        elif e.status_code == 404:
            logger.error("🔧 Error 404: Verifica que el endpoint y el índice existan")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error inesperado durante validación de Azure Search: {str(e)}")
        logger.debug(f"Tipo de error: {type(e).__name__}")
        return False


async def validate_search_credential_scope(credential) -> bool:
    """
    Valida específicamente que la credencial puede obtener tokens para Azure Search
    """
    try:
        logger.info("🔑 Validando scope de credencial para Azure Search...")
        
        # Probar diferentes scopes que Azure Search puede necesitar
        scopes_to_test = [
            "https://search.azure.com/.default",
            "https://management.azure.com/.default",
            "https://cognitiveservices.azure.com/.default"
        ]
        
        results = {}
        
        for scope in scopes_to_test:
            try:
                token = await credential.get_token(scope)
                if token and token.token:
                    results[scope] = {
                        "status": "success",
                        "expires_on": token.expires_on,
                        "token_length": len(token.token)
                    }
                    logger.info(f"✅ Token obtenido para scope: {scope}")
                else:
                    results[scope] = {"status": "failed", "error": "No token returned"}
                    logger.warning(f"⚠️ No se pudo obtener token para scope: {scope}")
                    
            except Exception as e:
                results[scope] = {"status": "error", "error": str(e)}
                logger.error(f"❌ Error obteniendo token para {scope}: {str(e)}")
        
        # Azure Search específicamente necesita el scope search.azure.com
        search_scope_success = results.get("https://search.azure.com/.default", {}).get("status") == "success"
        
        if search_scope_success:
            logger.info("✅ Credencial válida para Azure Search")
            return True
        else:
            logger.error("❌ Credencial no puede obtener tokens para Azure Search")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error validando scope de credencial: {str(e)}")
        return False


def validate_search_environment_vars() -> dict:
    """
    Valida que todas las variables de entorno necesarias para Azure Search estén configuradas
    """
    required_vars = {
        "AZURE_SEARCH_SERVICE": os.getenv("AZURE_SEARCH_SERVICE"),
        "AZURE_SEARCH_INDEX": os.getenv("AZURE_SEARCH_INDEX"),
    }
    
    optional_vars = {
        "AZURE_SEARCH_AGENT": os.getenv("AZURE_SEARCH_AGENT"),
        "AZURE_SEARCH_QUERY_LANGUAGE": os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us"),
        "AZURE_SEARCH_SEMANTIC_RANKER": os.getenv("AZURE_SEARCH_SEMANTIC_RANKER", "free"),
    }
    
    missing_required = [var for var, value in required_vars.items() if not value]
    
    if missing_required:
        logger.error(f"❌ Variables de entorno requeridas faltantes: {missing_required}")
        return {
            "status": "error",
            "missing_required": missing_required,
            "required_vars": required_vars,
            "optional_vars": optional_vars
        }
    
    # Construir endpoint
    search_service = required_vars["AZURE_SEARCH_SERVICE"]
    endpoint = f"https://{search_service}.search.windows.net"
    
    logger.info("✅ Variables de entorno para Azure Search configuradas correctamente")
    logger.info(f"📍 Endpoint: {endpoint}")
    logger.info(f"📋 Índice: {required_vars['AZURE_SEARCH_INDEX']}")
    
    return {
        "status": "success",
        "endpoint": endpoint,
        "required_vars": required_vars,
        "optional_vars": optional_vars
    }


# Función CLI para testing
async def main():
    """Función principal para testing desde CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validar acceso a Azure Search")
    parser.add_argument("--endpoint", help="Endpoint de Azure Search")
    parser.add_argument("--index", help="Nombre del índice")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logging verbose")
    
    args = parser.parse_args()
    
    # Configurar logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Validar variables de entorno
    env_check = validate_search_environment_vars()
    if env_check["status"] == "error":
        return False
    
    endpoint = args.endpoint or env_check["endpoint"]
    index_name = args.index or env_check["required_vars"]["AZURE_SEARCH_INDEX"]
    
    # Probar credencial
    try:
        credential = ManagedIdentityCredential()
        logger.info("🆔 Usando ManagedIdentityCredential")
    except Exception:
        try:
            credential = DefaultAzureCredential()
            logger.info("🆔 Usando DefaultAzureCredential")
        except Exception as e:
            logger.error(f"❌ No se pudo crear credencial: {e}")
            return False
    
    # Ejecutar validaciones
    scope_valid = await validate_search_credential_scope(credential)
    if not scope_valid:
        return False
    
    # Validación RBAC explícita (opcional, puede fallar sin impedir el funcionamiento)
    rbac_enabled = os.getenv("AZURE_VALIDATE_RBAC", "false").lower() == "true"
    if rbac_enabled:
        try:
            from .rbac_validation import validate_rbac_for_search
            logger.info("🔐 Ejecutando validación RBAC explícita...")
            rbac_valid = await validate_rbac_for_search()
            if not rbac_valid:
                logger.warning("⚠️ Validación RBAC explícita falló, pero continuando con validaciones funcionales...")
        except ImportError:
            logger.warning("⚠️ Módulo rbac_validation no disponible")
        except Exception as e:
            logger.warning(f"⚠️ Error en validación RBAC explícita: {str(e)}")
    
    access_valid = await validate_search_access(endpoint, credential, index_name)
    
    if access_valid:
        logger.info("🎉 Todas las validaciones de Azure Search pasaron exitosamente!")
        return True
    else:
        logger.error("💥 Falló la validación de acceso a Azure Search")
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    exit(0 if success else 1)
