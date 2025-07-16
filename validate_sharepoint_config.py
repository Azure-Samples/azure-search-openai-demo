#!/usr/bin/env python3
"""
Script de validación para configuración SharePoint
Ejecuta una serie de verificaciones para asegurar que la configuración es correcta
"""

import os
import sys
import json
import requests
from pathlib import Path

def check_environment_variables():
    """Verificar variables de entorno requeridas"""
    print("🔍 Verificando variables de entorno...")
    
    required_vars = [
        'AZURE_TENANT_ID',
        'AZURE_CLIENT_APP_ID', 
        'AZURE_CLIENT_APP_SECRET'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Variables faltantes: {', '.join(missing)}")
        return False
    else:
        print("✅ Variables de entorno configuradas correctamente")
        return True

def check_config_files():
    """Verificar archivos de configuración"""
    print("\n🔍 Verificando archivos de configuración...")
    
    config_dir = Path("app/backend/sharepoint_config")
    required_files = [
        "sharepoint_config.json",
        "sharepoint.env"
    ]
    
    missing = []
    for file in required_files:
        if not (config_dir / file).exists():
            missing.append(file)
    
    if missing:
        print(f"❌ Archivos faltantes: {', '.join(missing)}")
        return False
    else:
        print("✅ Archivos de configuración encontrados")
        return True

def check_app_running():
    """Verificar si la aplicación está corriendo"""
    print("\n🔍 Verificando si la aplicación está corriendo...")
    
    try:
        response = requests.get("http://localhost:50505/debug/sharepoint/config", timeout=5)
        if response.status_code == 200:
            print("✅ Aplicación corriendo correctamente")
            return True
        else:
            print(f"❌ Aplicación responde pero con error: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ Aplicación no está corriendo o no responde")
        return False

def test_sharepoint_config():
    """Probar configuración de SharePoint"""
    print("\n🔍 Probando configuración de SharePoint...")
    
    try:
        response = requests.get("http://localhost:50505/debug/sharepoint/config", timeout=10)
        if response.status_code == 200:
            config = response.json()
            print("✅ Configuración de SharePoint obtenida:")
            print(f"   📁 Carpetas de búsqueda: {config['config']['search_folders']}")
            print(f"   🔍 Keywords de sitios: {config['config']['site_keywords'][:3]}...")
            print(f"   🏢 Máximo sitios: {config['config']['max_sites_to_search']}")
            return True
        else:
            print("❌ Error obteniendo configuración de SharePoint")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_sharepoint_search():
    """Probar búsqueda en SharePoint"""
    print("\n🔍 Probando búsqueda en SharePoint...")
    
    try:
        response = requests.get("http://localhost:50505/debug/sharepoint/test-configured-folders", timeout=30)
        if response.status_code == 200:
            result = response.json()
            files_found = result.get('files_found', 0)
            print(f"✅ Búsqueda completada - {files_found} archivos encontrados")
            
            if files_found == 0:
                print("⚠️  No se encontraron archivos. Esto puede ser normal si:")
                print("   - Es la primera vez que configuras SharePoint")
                print("   - No hay documentos en las carpetas configuradas")
                print("   - Los permisos de la aplicación están pendientes")
            
            return True
        else:
            print("❌ Error en búsqueda de SharePoint")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Validador de Configuración SharePoint")
    print("=" * 50)
    
    checks = [
        check_environment_variables,
        check_config_files,
        check_app_running,
        test_sharepoint_config,
        test_sharepoint_search
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        if check():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Resultado: {passed}/{total} verificaciones pasadas")
    
    if passed == total:
        print("🎉 ¡Configuración completamente funcional!")
        print("\n💡 Próximos pasos:")
        print("   1. Crear documentos en tu SharePoint")
        print("   2. Probar chat con: '¿Qué documentos tienes disponibles?'")
        print("   3. Configurar carpetas específicas si es necesario")
    else:
        print("⚠️  Hay configuraciones pendientes")
        print("\n📖 Consulta la documentación en:")
        print("   - docs/sharepoint_configuration.md")
        print("   - docs/sharepoint_deployment_guide.md")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
