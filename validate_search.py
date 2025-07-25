#!/usr/bin/env python3
"""
Script CLI para validar Azure Search independientemente de la aplicación
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent / "app" / "backend"
sys.path.insert(0, str(backend_dir))

from healthchecks.search import validate_search_access, validate_search_credential_scope, validate_search_environment_vars


async def main():
    """Función principal del CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validar acceso a Azure Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Validación básica usando variables de entorno
  python validate_search.py
  
  # Validación con endpoint específico
  python validate_search.py --endpoint https://mi-search.search.windows.net --index mi-indice
  
  # Validación verbose con todos los detalles
  python validate_search.py --verbose
  
  # Solo validar credencial
  python validate_search.py --credential-only

Variables de entorno requeridas:
  AZURE_SEARCH_SERVICE - Nombre del servicio de Azure Search
  AZURE_SEARCH_INDEX - Nombre del índice
        """
    )
    
    parser.add_argument("--endpoint", help="Endpoint de Azure Search (ej: https://servicio.search.windows.net)")
    parser.add_argument("--index", help="Nombre del índice")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logging verbose")
    parser.add_argument("--credential-only", action="store_true", help="Solo validar credencial, sin acceso a Search")
    parser.add_argument("--strict", action="store_true", help="Fallar inmediatamente en cualquier error")
    
    args = parser.parse_args()
    
    # Configurar logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("validate_search")
    
    print("🔍 Azure Search Validation Tool")
    print("=" * 50)
    
    try:
        # Paso 1: Validar variables de entorno
        logger.info("📋 Validando variables de entorno...")
        env_check = validate_search_environment_vars()
        
        if env_check["status"] == "error":
            logger.error("❌ Error en variables de entorno")
            print(f"\n💥 Variables faltantes: {env_check['missing_required']}")
            print("\nConfigura las siguientes variables:")
            for var in env_check['missing_required']:
                print(f"  export {var}=<valor>")
            return False
        
        # Usar valores de argumentos o variables de entorno
        endpoint = args.endpoint or env_check["endpoint"]
        index_name = args.index or env_check["required_vars"]["AZURE_SEARCH_INDEX"]
        
        print(f"📍 Endpoint: {endpoint}")
        print(f"📋 Índice: {index_name}")
        
        # Paso 2: Crear credencial
        logger.info("🆔 Configurando credencial de Azure...")
        try:
            # Intentar ManagedIdentityCredential primero (para Container Apps)
            from azure.identity.aio import ManagedIdentityCredential
            credential = ManagedIdentityCredential()
            logger.info("✅ Usando ManagedIdentityCredential")
            print("🔑 Credencial: ManagedIdentityCredential (Container App)")
        except Exception:
            try:
                # Fallback a DefaultAzureCredential (para desarrollo local)
                from azure.identity.aio import DefaultAzureCredential
                credential = DefaultAzureCredential()
                logger.info("✅ Usando DefaultAzureCredential")
                print("🔑 Credencial: DefaultAzureCredential (desarrollo local)")
            except Exception as e:
                logger.error(f"❌ No se pudo crear credencial: {e}")
                print(f"💥 Error creando credencial: {e}")
                return False
        
        # Paso 3: Validar scope de credencial
        logger.info("🔑 Validando scope de credencial...")
        scope_valid = await validate_search_credential_scope(credential)
        
        if not scope_valid:
            logger.error("❌ Credencial no puede obtener tokens para Azure Search")
            print("\n💥 Error de credencial:")
            print("  - Verifica que el Container App tenga System-Assigned Managed Identity")
            print("  - Verifica que el MI tenga roles RBAC en Azure Search")
            print("  - Roles necesarios: Search Index Data Reader, Search Service Contributor")
            
            if args.strict:
                return False
        else:
            print("✅ Credencial válida para Azure Search")
        
        # Paso 4: Validar acceso (a menos que sea credential-only)
        if not args.credential_only:
            logger.info("🌐 Validando acceso completo a Azure Search...")
            access_valid = await validate_search_access(endpoint, credential, index_name)
            
            if access_valid:
                print("✅ Acceso completo a Azure Search validado")
                print("\n🎉 Todas las validaciones pasaron exitosamente!")
                return True
            else:
                logger.error("❌ Falló la validación de acceso a Azure Search")
                print("\n💥 Error de acceso:")
                print("  - Verifica que el endpoint sea correcto")
                print("  - Verifica que el índice exista")
                print("  - Verifica permisos RBAC")
                
                if args.strict:
                    return False
                else:
                    print("⚠️ Continuando (usar --strict para fallar)")
        else:
            print("ℹ️ Saltando validación de acceso (--credential-only)")
        
        if scope_valid:
            print("\n✅ Validación completada (con advertencias)")
            return True
        else:
            print("\n❌ Validación falló")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Validación cancelada por el usuario")
        return False
        
    except Exception as e:
        logger.error(f"💥 Error inesperado: {str(e)}")
        print(f"\n💥 Error inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Error fatal: {e}")
        sys.exit(1)
