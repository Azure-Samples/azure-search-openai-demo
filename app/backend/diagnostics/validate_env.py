"""
Validación de variables de entorno base
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

def validate_env_vars():
    """Valida variables de entorno básicas de Azure"""
    log_info("[ENV] Validando entorno general...")
    
    # Variables básicas de Azure
    azure_vars = [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID", 
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP"
    ]
    
    # Variables opcionales pero recomendadas
    optional_vars = [
        "AZURE_CLIENT_SECRET",
        "RUNNING_IN_PRODUCTION"
    ]
    
    all_good = True
    
    print("  Variables básicas de Azure:")
    for var in azure_vars:
        val = os.getenv(var)
        if val:
            print(f"    {var}: ✅ {val[:20]}{'...' if len(val) > 20 else ''}")
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
    
    if all_good:
        print("  ENV: ✅ Configuración básica completa")
        return 0
    else:
        print("  ENV: ❌ Faltan variables requeridas")
        return 1

if __name__ == "__main__":
    exit(validate_env_vars())
