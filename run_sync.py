#!/usr/bin/env python3

import os
import sys

def load_env_variables():
    """Cargar variables de entorno desde .env"""
    env_file = "/workspaces/azure-search-openai-demo/.env"
    
    if not os.path.exists(env_file):
        print("❌ Archivo .env no encontrado")
        return False
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    print("✅ Variables de entorno cargadas")
    return True

if __name__ == "__main__":
    if not load_env_variables():
        sys.exit(1)
    
    # Verificar variables críticas
    required_vars = [
        'AZURE_SEARCH_SERVICE',
        'AZURE_SEARCH_INDEX',
        'CLIENT_ID',
        'CLIENT_SECRET',
        'TENANT_ID',
        'SITE_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables faltantes: {missing_vars}")
        sys.exit(1)
    
    print("✅ Todas las variables críticas están presentes")
    
    # Ahora ejecutar la sincronización
    sys.path.insert(0, '/workspaces/azure-search-openai-demo/app/backend')
    
    try:
        import sync_sharepoint_to_index
        print("✅ Script de sincronización ejecutado")
    except Exception as e:
        print(f"❌ Error ejecutando sincronización: {e}")
        sys.exit(1)
