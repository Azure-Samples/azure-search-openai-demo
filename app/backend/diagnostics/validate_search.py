"""
Validación de configuración de Azure Search
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

def validate_search_config():
    """Valida la configuración de Azure Search"""
    log_info("[SEARCH] Validando configuración de Azure Search...")
    
    # Variables requeridas para Azure Search
    required_vars = [
        "AZURE_SEARCH_SERVICE",
        "AZURE_SEARCH_INDEX", 
        "AZURE_SEARCH_SERVICE_RESOURCE_GROUP"
    ]
    
    # Variables opcionales
    optional_vars = [
        "AZURE_SEARCH_SEMANTIC_RANKER",
        "AZURE_SEARCH_FIELD_NAME_EMBEDDING",
        "SEARCH_ENDPOINT",
        "SEARCH_INDEX"
    ]
    
    all_good = True
    
    print("  Variables requeridas de Search:")
    for var in required_vars:
        val = os.getenv(var)
        if val:
            print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ❌ No definida")
            all_good = False
    
    print("  Variables opcionales:")
    for var in optional_vars:
        val = os.getenv(var)
        if val:
            print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ⚠️ No definida (opcional)")
    
    # Intentar conectividad básica (si las variables están disponibles)
    search_endpoint = os.getenv("SEARCH_ENDPOINT") or os.getenv("AZURE_SEARCH_ENDPOINT")
    if search_endpoint:
        try:
            import requests
            # Ping básico al endpoint
            response = requests.get(f"{search_endpoint}/", timeout=10)
            if response.status_code == 200:
                print(f"    Conectividad: ✅ Endpoint responde")
            else:
                print(f"    Conectividad: ⚠️ Código {response.status_code}")
        except Exception as e:
            print(f"    Conectividad: ❌ Error: {str(e)[:100]}")
    
    if all_good:
        print("  SEARCH: ✅ Configuración completa")
        return 0
    else:
        print("  SEARCH: ❌ Faltan variables requeridas")
        return 1

if __name__ == "__main__":
    exit(validate_search_config())

import os
try:
    from .utils_logger import log_ok, log_error, log_info
except ImportError:
    # Fallback para ejecución directa
    def log_ok(msg): print("✅ " + msg)
    def log_error(msg): print("❌ " + msg)
    def log_info(msg): print("🔍 " + msg)

def validate_search_config():
    """Valida configuración de Azure Search"""
    log_info("[SEARCH] Validando configuración de Azure Search...")
    
    # Variables requeridas para Azure Search
    required_vars = [
        "AZURE_SEARCH_SERVICE",
        "AZURE_SEARCH_INDEX",
        "AZURE_SEARCH_SERVICE_RESOURCE_GROUP"
    ]
    
    # Variables opcionales
    optional_vars = [
        "AZURE_SEARCH_KEY",
        "AZURE_SEARCH_SEMANTIC_RANKER",
        "AZURE_SEARCH_FIELD_NAME_EMBEDDING"
    ]
    
    all_good = True
    
    print("  Variables requeridas:")
    for var in required_vars:
        val = os.getenv(var)
        if val:
            print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ❌ No definida")
            all_good = False
    
    print("  Variables opcionales:")
    for var in optional_vars:
        val = os.getenv(var)
        if val:
            print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ⚠️ No definida (opcional)")
    
    # Construir endpoint si es posible
    search_service = os.getenv("AZURE_SEARCH_SERVICE")
    if search_service:
        endpoint = f"https://{search_service}.search.windows.net"
        print(f"    Endpoint calculado: {endpoint}")
    
    if all_good:
        print("  SEARCH: ✅ Configuración completa")
        return 0
    else:
        print("  SEARCH: ❌ Faltan variables requeridas")
        return 1

def test_search_connection():
    """Prueba conexión real con Azure Search (requiere credenciales)"""
    try:
        from azure.search.documents import SearchClient
        from azure.identity import DefaultAzureCredential
        
        search_service = os.getenv("AZURE_SEARCH_SERVICE")
        search_index = os.getenv("AZURE_SEARCH_INDEX")
        
        if not search_service or not search_index:
            print("    ❌ Variables de Search no configuradas")
            return 1
            
        endpoint = f"https://{search_service}.search.windows.net"
        credential = DefaultAzureCredential()
        
        search_client = SearchClient(
            endpoint=endpoint,
            index_name=search_index,
            credential=credential
        )
        
        # Hacer una búsqueda de prueba
        results = search_client.search("test", top=1)
        list(results)  # Consumir el iterador
        
        print("    ✅ Conexión con Azure Search exitosa")
        return 0
        
    except Exception as e:
        print(f"    ❌ Error conectando con Azure Search: {str(e)}")
        return 1

if __name__ == "__main__":
    result = validate_search_config()
    if result == 0:
        result = test_search_connection()
    exit(result)
