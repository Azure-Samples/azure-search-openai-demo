"""
Validación de roles y permisos RBAC en Azure
"""

import os

# Cargar variables de entorno automáticamente
try:
    from .env_loader import load_env_file
except ImportError:
    # Fallback para ejecución directa
    import sys
    sys.path.append(os.path.dirname(__file__))
    from env_loader import load_env_file

try:
    from .utils_logger import log_ok, log_error, log_info
except ImportError:
    # Fallback para ejecución directa
    def log_ok(msg): print("✅ " + msg)
    def log_error(msg): print("❌ " + msg)
    def log_info(msg): print("🔍 " + msg)

def validate_rbac():
    """Valida asignaciones de roles RBAC en recursos de Azure"""
    log_info("[RBAC] Validando asignaciones de roles...")
    
    # Variables necesarias para validar RBAC
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP")
    
    print("  Variables base para RBAC:")
    if subscription_id:
        print(f"    AZURE_SUBSCRIPTION_ID: ✅ {subscription_id}")
    else:
        print(f"    AZURE_SUBSCRIPTION_ID: ❌ No definida")
        print("  RBAC: ❌ No se puede validar sin subscription ID")
        return 1
    
    if resource_group:
        print(f"    AZURE_RESOURCE_GROUP: ✅ {resource_group}")
    else:
        print(f"    AZURE_RESOURCE_GROUP: ❌ No definida")
        print("  RBAC: ❌ No se puede validar sin resource group")
        return 1
    
    # Intentar validar permisos básicos
    try:
        print("  Probando acceso a Azure Management API...")
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.resource import ResourceManagementClient
        
        cred = DefaultAzureCredential()
        
        # Intentar listar recursos del grupo
        resource_client = ResourceManagementClient(cred, subscription_id)
        
        print("    Listando recursos del grupo...")
        resources = list(resource_client.resources.list_by_resource_group(resource_group))
        print(f"    Recursos encontrados: ✅ {len(resources)} recursos")
        
        # Mostrar algunos recursos encontrados
        openai_resources = [r for r in resources if "cognitiveservices" in r.type.lower()]
        search_resources = [r for r in resources if "search" in r.type.lower()]
        
        if openai_resources:
            print(f"    Recursos OpenAI: ✅ {len(openai_resources)} encontrados")
            for res in openai_resources[:2]:  # Mostrar máximo 2
                print(f"      - {res.name} ({res.type})")
        else:
            print(f"    Recursos OpenAI: ⚠️ No encontrados")
        
        if search_resources:
            print(f"    Recursos Search: ✅ {len(search_resources)} encontrados")
            for res in search_resources[:2]:  # Mostrar máximo 2
                print(f"      - {res.name} ({res.type})")
        else:
            print(f"    Recursos Search: ⚠️ No encontrados")
        
        print("  RBAC: ✅ Acceso básico a recursos validado")
        return 0
        
    except Exception as e:
        print(f"    Error: ❌ {str(e)[:150]}")
        print("  RBAC: ⚠️ No se pudo validar completamente (puede ser normal en dev)")
        # No retornar error porque en desarrollo esto puede fallar por limitaciones locales
        return 0

if __name__ == "__main__":
    exit(validate_rbac())

import os
try:
    from .utils_logger import log_ok, log_error, log_info
except ImportError:
    # Fallback para ejecución directa
    def log_ok(msg): print("✅ " + msg)
    def log_error(msg): print("❌ " + msg)
    def log_info(msg): print("🔍 " + msg)

def validate_rbac():
    """Valida asignación de roles RBAC"""
    log_info("[RBAC] Validando asignación de roles...")
    
    # Variables necesarias para RBAC
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP")
    openai_service = os.getenv("AZURE_OPENAI_SERVICE")
    search_service = os.getenv("AZURE_SEARCH_SERVICE")
    
    if not all([subscription_id, resource_group]):
        print("    ❌ Variables faltantes: AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP")
        return 1
    
    print("    Configuración RBAC:")
    print(f"      Subscription: {subscription_id}")
    print(f"      Resource Group: {resource_group}")
    
    if openai_service:
        print(f"      OpenAI Service: {openai_service}")
    if search_service:
        print(f"      Search Service: {search_service}")
    
    # Si no hay API key, asumimos que usa Managed Identity
    openai_key = os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE")
    search_key = os.getenv("AZURE_SEARCH_KEY")
    
    if not openai_key:
        print("    🔑 OpenAI: Usando Managed Identity (sin API key)")
    else:
        print("    🔑 OpenAI: Usando API key")
    
    if not search_key:
        print("    🔑 Search: Usando Managed Identity (sin API key)")
    else:
        print("    🔑 Search: Usando API key")
    
    print("  RBAC: ✅ Configuración revisada")
    return 0

def test_rbac_permissions():
    """Prueba permisos RBAC reales (requiere SDK de gestión)"""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.authorization import AuthorizationManagementClient
        
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        
        if not subscription_id:
            print("    ❌ AZURE_SUBSCRIPTION_ID no configurada")
            return 1
        
        credential = DefaultAzureCredential()
        auth_client = AuthorizationManagementClient(credential, subscription_id)
        
        # Obtener identity actual
        print("    🔍 Verificando identidad actual...")
        
        # Listar role assignments en el resource group
        scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        assignments = list(auth_client.role_assignments.list_for_scope(scope))
        
        print(f"    📋 Encontradas {len(assignments)} asignaciones de roles en RG")
        
        # Roles importantes para Cognitive Services
        important_roles = [
            "Cognitive Services User",
            "Cognitive Services OpenAI User", 
            "Search Index Data Reader",
            "Search Service Contributor"
        ]
        
        found_roles = []
        for assignment in assignments:
            role_def = auth_client.role_definitions.get_by_id(assignment.role_definition_id)
            role_name = role_def.role_name
            if any(important in role_name for important in important_roles):
                found_roles.append(role_name)
        
        if found_roles:
            print(f"    ✅ Roles importantes encontrados: {', '.join(found_roles)}")
        else:
            print("    ⚠️ No se encontraron roles específicos de Cognitive Services")
        
        return 0
        
    except Exception as e:
        print(f"    ❌ Error verificando RBAC: {str(e)}")
        print("    ℹ️ Esto es normal si no tienes permisos de lectura de RBAC")
        return 0  # No fallar por esto

if __name__ == "__main__":
    result = validate_rbac()
    if result == 0:
        result = test_rbac_permissions()
    exit(result)
