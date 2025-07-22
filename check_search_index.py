#!/usr/bin/env python3

import os
import sys
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

def check_search_index():
    """Verificar el estado del índice de Azure AI Search"""
    
    # Configuración desde variables de entorno
    service_name = "srch-volaris-dev-eus-001" 
    index_name = "idx-volaris-dev-eus-001"
    
    search_endpoint = f"https://{service_name}.search.windows.net"
    
    # Usar identidad administrada por defecto
    credential = DefaultAzureCredential()
    
    try:
        # Crear cliente del índice
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        print("=== VERIFICACIÓN DEL ÍNDICE DE AZURE AI SEARCH ===")
        
        # Listar todos los índices
        print("1. Listando índices disponibles:")
        indexes = list(index_client.list_index_names())  # Convertir a lista primero
        for idx in indexes:
            print(f"   - {idx}")
        
        print(f"\n   Verificando si '{index_name}' está en la lista...")
        print(f"   Índices encontrados: {indexes}")
        print(f"   ¿'{index_name}' en lista? {index_name in indexes}")
        
        if index_name not in indexes:
            print(f"❌ ERROR: El índice '{index_name}' no existe!")
            return False
        
        # Obtener estadísticas del índice
        print(f"\n2. Verificando estadísticas del índice '{index_name}':")
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Intentar buscar documentos para verificar si hay contenido
        results = search_client.search(search_text="*", top=5, include_total_count=True)
        
        print(f"   - Total de documentos: {results.get_count()}")
        
        # Mostrar algunos documentos de ejemplo
        print(f"\n3. Ejemplos de documentos indexados:")
        count = 0
        for result in results:
            count += 1
            print(f"   Documento {count}:")
            if 'unique_id' in result:
                print(f"     - unique_id: {result['unique_id']}")
            if 'sourcefile' in result:
                print(f"     - sourcefile: {result['sourcefile']}")
            if 'content' in result:
                content_preview = result['content'][:100] if result['content'] else "No content"
                print(f"     - content: {content_preview}...")
            print()
            
        if count == 0:
            print("   ❌ No se encontraron documentos en el índice!")
            return False
        else:
            print(f"   ✅ Se encontraron documentos en el índice")
            return True
            
    except Exception as e:
        print(f"❌ ERROR al verificar el índice: {e}")
        return False

if __name__ == "__main__":
    success = check_search_index()
    sys.exit(0 if success else 1)
