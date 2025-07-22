#!/usr/bin/env python3

import os
import sys

def setup_environment():
    """Setup environment variables"""
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
    
    return True

def get_index_schema():
    """Obtener el esquema del índice"""
    
    try:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.identity import DefaultAzureCredential
        
        search_service = os.getenv("AZURE_SEARCH_SERVICE")
        search_index = os.getenv("AZURE_SEARCH_INDEX")
        
        credential = DefaultAzureCredential()
        search_endpoint = f"https://{search_service}.search.windows.net"
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        print(f"=== ESQUEMA DEL ÍNDICE: {search_index} ===")
        
        # Obtener definición del índice
        index = index_client.get_index(search_index)
        
        print(f"Nombre del índice: {index.name}")
        print(f"Campos disponibles:")
        
        for field in index.fields:
            field_info = f"  - {field.name} ({field.type})"
            if field.key:
                field_info += " [KEY]"
            if field.searchable:
                field_info += " [SEARCHABLE]"
            if field.filterable:
                field_info += " [FILTERABLE]"
            print(field_info)
        
        # Buscar el campo key
        key_field = None
        for field in index.fields:
            if field.key:
                key_field = field.name
                break
        
        print(f"\nCampo clave: {key_field}")
        
        return key_field, index.fields
        
    except Exception as e:
        print(f"❌ Error obteniendo esquema: {e}")
        return None, None

def main():
    if not setup_environment():
        return False
    
    key_field, fields = get_index_schema()
    return key_field is not None

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
