#!/usr/bin/env python3
"""
Script para ejecutar el checklist completo de validación
Detecta automáticamente el entorno y ejecuta las validaciones correspondientes
"""

import os
import sys
from pathlib import Path

# Agregar el directorio de diagnostics al path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

try:
    from environment_detector import detect_environment, EnvironmentType
    from deployment_checklist import run_checklist
    from utils_logger import log_ok, log_error, log_info
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("🔍 Asegúrate de que todos los módulos de diagnósticos estén presentes")
    sys.exit(1)

def explain_checklist():
    """Explica qué hace cada validación del checklist"""
    print("""
🚀 CHECKLIST DE VALIDACIÓN COMPLETO

Este script ejecuta una serie de validaciones para asegurar que el entorno
está correctamente configurado para Azure Search + OpenAI:

📋 VALIDACIONES INCLUIDAS:

🌍 [ENV] Validación de Entorno
   ✓ Variables de Azure (TENANT_ID, SUBSCRIPTION_ID, etc.)
   ✓ Configuración de autenticación
   ✓ Variables específicas del proyecto

🔍 [SEARCH] Validación de Azure Search
   ✓ Conectividad al servicio
   ✓ Existencia del índice configurado
   ✓ Permisos de lectura/escritura
   ✓ Configuración de embeddings

🤖 [OPENAI] Validación de Azure OpenAI
   ✓ Conectividad al servicio
   ✓ Disponibilidad del modelo/deployment
   ✓ Permisos de acceso
   ✓ Prueba de llamada de chat completion

🔐 [RBAC] Validación de Roles y Permisos
   ✓ Asignaciones de roles en recursos
   ✓ Permisos de Managed Identity
   ✓ Acceso a servicios cognitivos

🎯 USO:
   python run_full_checklist.py              # Ejecuta todas las validaciones
   python run_full_checklist.py --explain    # Muestra esta explicación
   python run_full_checklist.py --env-only   # Solo validación de entorno
   python run_full_checklist.py --core       # Solo env, search, openai (sin RBAC)

🔄 DETECCIÓN AUTOMÁTICA DE ENTORNO:
   El script detecta automáticamente si está ejecutándose en:
   - GitHub Codespaces
   - Azure Container Apps
   - Azure App Service
   - Desarrollo local
   
   Y ajusta las validaciones según el contexto.
""")

def main():
    """Función principal del checklist completo"""
    
    # Parsear argumentos simples
    if len(sys.argv) > 1:
        if "--explain" in sys.argv:
            explain_checklist()
            return 0
        elif "--env-only" in sys.argv:
            checks = ["env"]
        elif "--core" in sys.argv:
            checks = ["env", "search", "openai"]
        else:
            checks = None  # Todas las validaciones
    else:
        checks = None  # Todas las validaciones
    
    print("🚀 INICIANDO CHECKLIST COMPLETO DE VALIDACIÓN")
    print("=" * 60)
    
    # Detectar entorno
    try:
        env_type = detect_environment()
        log_info(f"Entorno detectado: {env_type.value}")
        
        # Ajustar validaciones según el entorno
        if env_type == EnvironmentType.GITHUB_CODESPACES:
            log_info("Configuración para GitHub Codespaces")
        elif env_type == EnvironmentType.AZURE_CONTAINER_APPS:
            log_info("Configuración para Azure Container Apps")
            os.environ["RUNNING_IN_PRODUCTION"] = "true"
        elif env_type == EnvironmentType.AZURE_APP_SERVICE:
            log_info("Configuración para Azure App Service")
            os.environ["RUNNING_IN_PRODUCTION"] = "true"
        else:
            log_info("Configuración para desarrollo local")
            
    except Exception as e:
        log_error(f"Error detectando entorno: {e}")
        log_info("Continuando con configuración por defecto...")
    
    print("=" * 60)
    
    # Ejecutar el checklist
    try:
        exit_code = run_checklist(checks)
        
        print("=" * 60)
        if exit_code == 0:
            log_ok("🎉 TODOS LOS CHECKS PASARON EXITOSAMENTE")
            log_info("El entorno está listo para producción")
        else:
            log_error("💥 ALGUNOS CHECKS FALLARON")
            log_info("Revisa los errores anteriores y corrige la configuración")
        
        return exit_code
        
    except Exception as e:
        log_error(f"Error ejecutando checklist: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
