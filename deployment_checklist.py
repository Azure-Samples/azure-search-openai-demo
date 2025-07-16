#!/usr/bin/env python3
"""
Checklist de Configuración para Publicación del Chatbot de Pilotos
"""

import os
import json
import subprocess
from pathlib import Path

def check_environment_variables():
    """Verifica las variables de entorno necesarias"""
    print("\n🔧 VERIFICANDO VARIABLES DE ENTORNO")
    print("=" * 50)
    
    # Variables para Azure OpenAI
    azure_openai_vars = [
        "AZURE_OPENAI_SERVICE",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT", 
        "AZURE_OPENAI_CHATGPT_MODEL",
        "AZURE_OPENAI_EMB_DEPLOYMENT",
        "AZURE_OPENAI_EMB_MODEL_NAME",
        "AZURE_OPENAI_EMB_DIMENSIONS"
    ]
    
    # Variables para Azure AI Search
    azure_search_vars = [
        "AZURE_SEARCH_SERVICE",
        "AZURE_SEARCH_INDEX",
        "AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG"
    ]
    
    # Variables para Azure Storage
    azure_storage_vars = [
        "AZURE_STORAGE_ACCOUNT",
        "AZURE_STORAGE_CONTAINER"
    ]
    
    # Variables para SharePoint (NUEVAS)
    sharepoint_vars = [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_APP_ID", 
        "AZURE_CLIENT_APP_SECRET"
    ]
    
    # Variables de autenticación (opcional)
    auth_vars = [
        "AZURE_USE_AUTHENTICATION",
        "AZURE_SERVER_APP_ID",
        "AZURE_SERVER_APP_SECRET",
        "AZURE_CLIENT_APP_ID",
        "AZURE_TENANT_ID"
    ]
    
    all_vars = {
        "Azure OpenAI": azure_openai_vars,
        "Azure AI Search": azure_search_vars, 
        "Azure Storage": azure_storage_vars,
        "SharePoint Integration": sharepoint_vars,
        "Authentication (Opcional)": auth_vars
    }
    
    missing_critical = []
    missing_optional = []
    
    for category, vars_list in all_vars.items():
        print(f"\n📋 {category}:")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                # Ocultar secretos
                if "SECRET" in var or "KEY" in var:
                    display_value = "***" + value[-4:] if len(value) > 4 else "***"
                else:
                    display_value = value[:50] + "..." if len(value) > 50 else value
                print(f"   ✅ {var} = {display_value}")
            else:
                print(f"   ❌ {var} = (no configurada)")
                if category == "Authentication (Opcional)":
                    missing_optional.append(var)
                else:
                    missing_critical.append(var)
    
    return missing_critical, missing_optional

def check_azure_resources():
    """Verifica que los recursos de Azure estén disponibles"""
    print("\n☁️  VERIFICANDO RECURSOS DE AZURE")
    print("=" * 50)
    
    # Verificar si Azure CLI está instalado
    try:
        result = subprocess.run(['az', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Azure CLI instalado")
        else:
            print("❌ Azure CLI no está instalado o no funciona")
            return False
    except FileNotFoundError:
        print("❌ Azure CLI no encontrado")
        return False
    
    # Verificar login en Azure
    try:
        result = subprocess.run(['az', 'account', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            account = json.loads(result.stdout)
            print(f"✅ Logueado en Azure: {account.get('user', {}).get('name', 'Unknown')}")
            print(f"   📋 Suscripción: {account.get('name', 'Unknown')}")
        else:
            print("❌ No está logueado en Azure - ejecutar 'az login'")
            return False
    except Exception as e:
        print(f"❌ Error verificando login Azure: {e}")
        return False
    
    return True

def check_sharepoint_configuration():
    """Verifica la configuración específica de SharePoint"""
    print("\n📁 VERIFICANDO CONFIGURACIÓN DE SHAREPOINT")
    print("=" * 50)
    
    required_vars = ["AZURE_TENANT_ID", "AZURE_CLIENT_APP_ID", "AZURE_CLIENT_APP_SECRET"]
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print("❌ Variables de SharePoint faltantes:")
        for var in missing:
            print(f"   - {var}")
        print("\n📋 Para configurar SharePoint:")
        print("   1. Registrar aplicación en Azure AD")
        print("   2. Configurar permisos: Sites.Read.All, Files.Read.All")
        print("   3. Generar secreto de cliente")
        print("   4. Establecer variables de entorno")
        return False
    else:
        print("✅ Variables de SharePoint configuradas")
        print("⚠️  Nota: Verificar que la aplicación tenga permisos correctos")
        return True

def check_infrastructure():
    """Verifica los archivos de infraestructura"""
    print("\n🏗️  VERIFICANDO INFRAESTRUCTURA")
    print("=" * 50)
    
    required_files = [
        "/workspaces/azure-search-openai-demo/azure.yaml",
        "/workspaces/azure-search-openai-demo/infra/main.bicep",
        "/workspaces/azure-search-openai-demo/infra/main.parameters.json"
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {os.path.basename(file_path)}")
        else:
            print(f"❌ {os.path.basename(file_path)} - No encontrado")
            all_exist = False
    
    return all_exist

def check_dependencies():
    """Verifica las dependencias del proyecto"""
    print("\n📦 VERIFICANDO DEPENDENCIAS")
    print("=" * 50)
    
    # Verificar backend dependencies
    backend_req = "/workspaces/azure-search-openai-demo/app/backend/requirements.txt"
    if os.path.exists(backend_req):
        print("✅ requirements.txt (backend)")
    else:
        print("❌ requirements.txt (backend) no encontrado")
    
    # Verificar frontend dependencies  
    frontend_pkg = "/workspaces/azure-search-openai-demo/app/frontend/package.json"
    if os.path.exists(frontend_pkg):
        print("✅ package.json (frontend)")
    else:
        print("❌ package.json (frontend) no encontrado")
    
    # Verificar archivos de integración SharePoint
    sharepoint_files = [
        "/workspaces/azure-search-openai-demo/app/backend/core/graph.py",
        "/workspaces/azure-search-openai-demo/SHAREPOINT_INTEGRATION.md"
    ]
    
    for file_path in sharepoint_files:
        if os.path.exists(file_path):
            print(f"✅ {os.path.basename(file_path)} (SharePoint)")
        else:
            print(f"❌ {os.path.basename(file_path)} (SharePoint) no encontrado")

def generate_deployment_guide():
    """Genera una guía de despliegue"""
    print("\n📖 GENERANDO GUÍA DE DESPLIEGUE")
    print("=" * 50)
    
    guide_content = """
# 🚀 Guía de Despliegue - Chatbot para Pilotos

## 🔧 Pre-requisitos

### 1. Azure CLI
```bash
# Instalar Azure CLI si no está instalado
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login en Azure
az login
```

### 2. Variables de Entorno Requeridas
```bash
# Azure OpenAI
export AZURE_OPENAI_SERVICE="tu-servicio-openai"
export AZURE_OPENAI_CHATGPT_DEPLOYMENT="tu-deployment-chat"
export AZURE_OPENAI_CHATGPT_MODEL="gpt-4"
export AZURE_OPENAI_EMB_DEPLOYMENT="tu-deployment-embeddings"
export AZURE_OPENAI_EMB_MODEL_NAME="text-embedding-ada-002"
export AZURE_OPENAI_EMB_DIMENSIONS="1536"

# Azure AI Search
export AZURE_SEARCH_SERVICE="tu-servicio-search"
export AZURE_SEARCH_INDEX="tu-indice"
export AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG="default"

# Azure Storage
export AZURE_STORAGE_ACCOUNT="tu-storage-account"
export AZURE_STORAGE_CONTAINER="tu-container"

# SharePoint Integration (NUEVO)
export AZURE_TENANT_ID="tu-tenant-id"
export AZURE_CLIENT_APP_ID="tu-app-id"
export AZURE_CLIENT_APP_SECRET="tu-app-secret"
```

## 🏗️ Despliegue con Azure Developer CLI (AZD)

### 1. Inicializar proyecto
```bash
cd /workspaces/azure-search-openai-demo
azd init
```

### 2. Configurar ambiente
```bash
azd env set AZURE_OPENAI_SERVICE "tu-servicio"
azd env set AZURE_SEARCH_SERVICE "tu-search"
# ... (configurar todas las variables)
```

### 3. Desplegar infraestructura y aplicación
```bash
azd up
```

## 📁 Configuración de SharePoint

### 1. Registrar aplicación en Azure AD
1. Ir a Azure Portal → Azure Active Directory → App registrations
2. Crear nueva aplicación
3. Configurar permisos API:
   - Microsoft Graph → Sites.Read.All
   - Microsoft Graph → Files.Read.All
4. Generar secreto de cliente

### 2. Verificar carpeta "Pilotos"
1. Acceder a SharePoint
2. Verificar que existe carpeta "Pilotos" 
3. Subir documentos relevantes para pilotos
4. Configurar permisos de acceso

## 🧪 Verificación Post-Despliegue

### 1. Probar funcionalidad básica
- Acceder a la URL del chatbot
- Hacer pregunta general → debe usar Azure AI Search
- Hacer pregunta sobre pilotos → debe usar SharePoint también

### 2. Ejemplos de prueba
- "¿Qué documentos para pilotos están disponibles?"
- "Muéstrame los procedimientos de cabina"
- "¿Cuáles son los requisitos de certificación?"

### 3. Verificar logs
```bash
azd logs
```

## 🔒 Seguridad y Consideraciones

1. **Secretos**: Nunca exponer secretos en código
2. **Permisos**: Principio de menor privilegio
3. **HTTPS**: Asegurar comunicación encriptada
4. **Monitoreo**: Configurar alertas y logging

## 📞 Soporte

Para problemas:
1. Revisar logs de aplicación
2. Verificar variables de entorno
3. Comprobar permisos de SharePoint
4. Validar recursos de Azure
"""
    
    guide_path = "/workspaces/azure-search-openai-demo/DEPLOYMENT_GUIDE.md"
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"✅ Guía creada: {guide_path}")

def main():
    print("🚀 CHECKLIST DE CONFIGURACIÓN PARA PUBLICACIÓN")
    print("🛩️  Chatbot AI para Pilotos de Aerolíneas")
    print("=" * 60)
    
    # Ejecutar verificaciones
    missing_critical, missing_optional = check_environment_variables()
    azure_ok = check_azure_resources()
    sharepoint_ok = check_sharepoint_configuration()
    infra_ok = check_infrastructure()
    check_dependencies()
    
    # Generar guía
    generate_deployment_guide()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PREPARACIÓN PARA PUBLICACIÓN")
    print("=" * 60)
    
    if missing_critical:
        print("❌ CRÍTICO - Variables faltantes:")
        for var in missing_critical:
            print(f"   - {var}")
    
    if missing_optional:
        print("⚠️  OPCIONAL - Variables de autenticación:")
        for var in missing_optional:
            print(f"   - {var}")
    
    status_items = [
        ("Variables críticas", len(missing_critical) == 0),
        ("Azure CLI", azure_ok),
        ("SharePoint config", sharepoint_ok),
        ("Infraestructura", infra_ok)
    ]
    
    print("\n🎯 Estado de componentes:")
    for item, status in status_items:
        icon = "✅" if status else "❌"
        print(f"   {icon} {item}")
    
    all_ready = all(status for _, status in status_items) and len(missing_critical) == 0
    
    if all_ready:
        print("\n🎉 ¡LISTO PARA PUBLICAR!")
        print("   Ejecutar: azd up")
    else:
        print("\n⚠️  NECESITA CONFIGURACIÓN")
        print("   Revisar elementos marcados arriba")
    
    print("\n📖 Consultar: DEPLOYMENT_GUIDE.md para instrucciones detalladas")

if __name__ == "__main__":
    main()
