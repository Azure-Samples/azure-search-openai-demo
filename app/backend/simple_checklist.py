#!/usr/bin/env python3
"""
Checklist simplificado para desarrollo local
Valida las configuraciones básicas sin necesidad de autenticación compleja
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Carga variables de entorno desde .azure/dev/.env"""
    env_paths = [
        Path(__file__).parent.parent / ".azure" / "dev" / ".env",
        Path(__file__).parent.parent.parent / ".azure" / "dev" / ".env",
        Path.cwd() / ".azure" / "dev" / ".env"
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            print(f"🔍 Cargando variables desde: {env_path}")
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Limpiar comillas
                        value = value.strip('"').strip("'")
                        os.environ[key] = value
            return True
    
    print("⚠️ No se encontró archivo .azure/dev/.env")
    return False

def simple_check_azure_cli():
    """Verifica que Azure CLI esté disponible y autenticado"""
    print("\n🔍 [CLI] Verificando Azure CLI...")
    
    try:
        import subprocess
        result = subprocess.run(['az', 'account', 'show'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            import json
            account = json.loads(result.stdout)
            print(f"    Usuario: ✅ {account.get('user', {}).get('name', 'N/A')}")
            print(f"    Tenant: ✅ {account.get('tenantId', 'N/A')[:8]}...")
            print(f"    Subscription: ✅ {account.get('name', 'N/A')}")
            return True
        else:
            print(f"    Error: ❌ {result.stderr}")
            return False
            
    except Exception as e:
        print(f"    Error: ❌ {str(e)}")
        return False

def simple_check_search():
    """Verifica configuración básica de Azure Search"""
    print("\n🔍 [SEARCH] Verificando configuración de Search...")
    
    required_vars = [
        "AZURE_SEARCH_SERVICE",
        "AZURE_SEARCH_INDEX",
        "SEARCH_ENDPOINT"
    ]
    
    all_good = True
    for var in required_vars:
        val = os.getenv(var)
        if val:
            print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ❌ No definida")
            all_good = False
    
    return all_good

def simple_check_openai():
    """Verifica configuración básica de Azure OpenAI"""
    print("\n🔍 [OPENAI] Verificando configuración de OpenAI...")
    
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT",
        "AZURE_OPENAI_CHATGPT_MODEL"
    ]
    
    all_good = True
    for var in required_vars:
        val = os.getenv(var)
        if val:
            # Mostrar endpoint truncado por seguridad
            display_val = val if "ENDPOINT" not in var else val[:50] + "..."
            print(f"    {var}: ✅ {display_val}")
        else:
            print(f"    {var}: ❌ No definida")
            all_good = False
    
    return all_good

def main():
    """Función principal del checklist simple"""
    print("🚀 CHECKLIST SIMPLE DE DESARROLLO")
    print("=" * 50)
    
    # Cargar variables de entorno
    load_env_file()
    
    # Ejecutar checks básicos
    cli_ok = simple_check_azure_cli()
    search_ok = simple_check_search()
    openai_ok = simple_check_openai()
    
    print("\n" + "=" * 50)
    print("📋 RESUMEN:")
    print(f"   Azure CLI: {'✅' if cli_ok else '❌'}")
    print(f"   Azure Search: {'✅' if search_ok else '❌'}")
    print(f"   Azure OpenAI: {'✅' if openai_ok else '❌'}")
    
    if all([cli_ok, search_ok, openai_ok]):
        print("\n🎉 TODOS LOS CHECKS BÁSICOS PASARON")
        print("✅ El entorno está listo para desarrollo")
        return 0
    else:
        print("\n⚠️ ALGUNOS CHECKS FALLARON")
        print("🔧 Revisa la configuración antes de continuar")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
