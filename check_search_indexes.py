#!/usr/bin/env python3
"""
Script para encontrar los índices reales en Azure Search
"""

import os
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient

def list_search_indexes():
    """Lista todos los índices disponibles en Azure Search"""
    try:
        # Configuración
        search_service = os.getenv("AZURE_SEARCH_SERVICE", "srch-volaris-dev-eus-001")
        credential = DefaultAzureCredential()
        
        # Cliente para gestión de índices
        index_client = SearchIndexClient(
            endpoint=f"https://{search_service}.search.windows.net",
            credential=credential
        )
        
        print(f"🔍 Listando índices en: {search_service}")
        print("=" * 50)
        
        # Listar todos los índices
        indexes = index_client.list_indexes()
        
        index_names = []
        for index in indexes:
            print(f"📋 Índice encontrado: {index.name}")
            print(f"   - Campos: {len(index.fields)} campos")
            print(f"   - Vectorial: {'Sí' if any(field.vector_search_dimensions for field in index.fields) else 'No'}")
            print()
            index_names.append(index.name)
        
        if not index_names:
            print("❌ No se encontraron índices")
        else:
            print(f"✅ Total de índices encontrados: {len(index_names)}")
            print(f"📝 Nombres: {', '.join(index_names)}")
            
        return index_names
        
    except Exception as e:
        print(f"🔴 Error al listar índices: {e}")
        print(f"📛 Tipo: {type(e)}")
        return []

if __name__ == "__main__":
    list_search_indexes()
