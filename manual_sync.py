#!/usr/bin/env python3

import os
import sys
import asyncio
import tempfile
from datetime import datetime

def setup_environment():
    """Setup environment variables and Python path"""
    # Cargar variables de entorno desde .env
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
    
    # Agregar path del backend
    backend_path = '/workspaces/azure-search-openai-demo/app/backend'
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    print("✅ Environment configurado")
    return True

def sync_sharepoint_documents():
    """Sincronizar documentos de SharePoint a Azure AI Search"""
    
    print("=== INICIO DE SINCRONIZACIÓN SHAREPOINT ===")
    
    # Importar módulos necesarios
    try:
        from azure.search.documents import SearchClient
        from azure.identity import DefaultAzureCredential
        from core.graph import get_access_token, get_drive_id, list_pilotos_files, get_file_content
        print("✅ Módulos importados correctamente")
    except Exception as e:
        print(f"❌ Error importando módulos: {e}")
        return False
    
    # Configuración
    search_service = os.getenv("AZURE_SEARCH_SERVICE")
    search_index = os.getenv("AZURE_SEARCH_INDEX")
    site_id = os.getenv("SITE_ID")
    
    print(f"Search Service: {search_service}")
    print(f"Search Index: {search_index}")
    print(f"Site ID: {site_id}")
    
    if not search_service or not search_index or not site_id:
        print("❌ Variables necesarias no configuradas")
        return False
    
    try:
        # Obtener token de acceso para SharePoint
        print("1. Obteniendo token de acceso...")
        access_token = get_access_token()
        
        # Obtener Drive ID
        print("2. Obteniendo Drive ID...")
        drive_id = get_drive_id(site_id, access_token)
        
        # Listar archivos de pilotos
        print("3. Listando archivos de SharePoint...")
        files = list_pilotos_files(drive_id, access_token)
        print(f"   Encontrados {len(files)} archivos")
        
        # Crear cliente de búsqueda
        print("4. Creando cliente de Azure AI Search...")
        credential = DefaultAzureCredential()
        search_endpoint = f"https://{search_service}.search.windows.net"
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=search_index,
            credential=credential
        )
        
        print("5. Procesando archivos...")
        docs_to_index = []
        
        for i, file in enumerate(files[:10]):  # CAMBIAR A files[:200] PARA INDEXACIÓN COMPLETA
            try:
                print(f"   Procesando {i+1}/10: {file['name']}")  # CAMBIAR A {i+1}/200 PARA INDEXACIÓN COMPLETA
                
                # Obtener contenido del archivo
                content = get_file_content(drive_id, file['id'], access_token)
                
                if not content or len(content.strip()) == 0:
                    print(f"   ⚠️ Contenido vacío para {file['name']}")
                    continue
                
                # Crear documento para indexar
                doc = {
                    "id": f"sharepoint_{file['id']}",  # Campo clave
                    "content": content,
                    "sourcefile": file['name'],
                    "sourcepage": file['name'],  # Usar filename como sourcepage
                    "category": "sharepoint",
                    "storageUrl": file.get('webUrl', '')
                }
                
                docs_to_index.append(doc)
                print(f"   ✅ Documento preparado: {file['name']} ({len(content)} chars)")
                
            except Exception as e:
                print(f"   ❌ Error procesando {file['name']}: {e}")
                continue
        
        if docs_to_index:
            print(f"\n6. Indexando {len(docs_to_index)} documentos...")
            
            # Indexar documentos
            try:
                result = search_client.upload_documents(docs_to_index)
                print(f"   ✅ Indexación completada")
                
                # Mostrar resultados
                for action in result:
                    if action.succeeded:
                        print(f"   ✅ Éxito: {action.key}")
                    else:
                        print(f"   ❌ Error: {action.key} - {action.error_message}")
                        
            except Exception as e:
                print(f"   ❌ Error durante indexación: {e}")
                return False
                
        else:
            print("   ❌ No hay documentos para indexar")
            return False
        
        print("\n=== SINCRONIZACIÓN COMPLETADA ===")
        return True
        
    except Exception as e:
        print(f"❌ Error durante sincronización: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    if not setup_environment():
        return False
    
    success = sync_sharepoint_documents()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
