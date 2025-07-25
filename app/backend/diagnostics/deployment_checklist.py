"""
Orquestador principal del checklist de validación
"""

import sys
import os

try:
    from .validate_env import validate_env_vars
    from .validate_search import validate_search_config
    from .validate_openai import validate_openai_access
    from .validate_rbac import validate_rbac
    from .utils_logger import log_ok, log_error, log_info
except ImportError:
    # Fallback para ejecución directa
    from validate_env import validate_env_vars
    from validate_search import validate_search_config
    from validate_openai import validate_openai_access
    from validate_rbac import validate_rbac
    def log_ok(msg): print("✅ " + msg)
    def log_error(msg): print("❌ " + msg)
    def log_info(msg): print("🔍 " + msg)

def run_checklist(checks=None):
    """
    Ejecuta el checklist de validación modular
    
    Args:
        checks: Lista de validaciones a ejecutar ['env', 'search', 'openai', 'rbac']
                Si es None, ejecuta todas
    
    Returns:
        int: Código de salida (0 = éxito, 1+ = errores)
    """
    print("\n🚀 Checklist de validación iniciado...\n")
    
    if checks is None:
        checks = ['env', 'search', 'openai', 'rbac']
    
    exit_code = 0
    results = {}
    
    if "env" in checks:
        try:
            result = validate_env_vars()
            results['env'] = result
            if result != 0:
                exit_code = 1
        except Exception as e:
            print(f"❌ Error en validación ENV: {e}")
            results['env'] = 1
            exit_code = 1
    
    if "search" in checks:
        try:
            result = validate_search_config()
            results['search'] = result
            if result != 0:
                exit_code = 1
        except Exception as e:
            print(f"❌ Error en validación SEARCH: {e}")
            results['search'] = 1
            exit_code = 1
    
    if "openai" in checks:
        try:
            result = validate_openai_access()
            results['openai'] = result
            if result != 0:
                exit_code = 1
        except Exception as e:
            print(f"❌ Error en validación OPENAI: {e}")
            results['openai'] = 1
            exit_code = 1
    
    if "rbac" in checks:
        try:
            result = validate_rbac()
            results['rbac'] = result
            if result != 0:
                exit_code = 1
        except Exception as e:
            print(f"❌ Error en validación RBAC: {e}")
            results['rbac'] = 1
            exit_code = 1
    
    # Resumen final
    print("\n📊 Resumen de validación:")
    for check, result in results.items():
        status = "✅" if result == 0 else "❌"
        print(f"  {check.upper()}: {status}")
    
    if exit_code == 0:
        print("\n✅ Validación completada exitosamente.")
    else:
        print("\n❌ Validación completada con errores.")
    
    return exit_code

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Checklist modular pre-deployment")
    parser.add_argument(
        "--check", 
        nargs="+", 
        choices=['env', 'search', 'openai', 'rbac'],
        help="Validaciones a ejecutar. Default: todas"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Salida detallada"
    )
    
    args = parser.parse_args()
    
    exit_code = run_checklist(args.check)
    sys.exit(exit_code)
