#!/usr/bin/env python3
"""
Script específico para diagnosticar acceso a Azure Search desde Container App
"""
import asyncio
import aiohttp
import os
import sys
import traceback
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from azure.search.documents.aio import SearchClient
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError


async def detailed_search_diagnosis():
    """Diagnóstico detallado del acceso a Azure Search"""
    
    # Variables de entorno
    search_service = os.getenv("AZURE_SEARCH_SERVICE")
    search_index = os.getenv("AZURE_SEARCH_INDEX")
    endpoint = f"https://{search_service}.search.windows.net"
    
    print("=== DIAGNÓSTICO DETALLADO AZURE SEARCH ===")
    print(f"Endpoint: {endpoint}")
    print(f"Index: {search_index}")
    print()
    
    # Parte 0: Validación RBAC explícita
    print("0. VALIDACIÓN RBAC EXPLÍCITA...")
    try:
        from healthchecks.rbac_validation import get_rbac_status_dict
        rbac_status = await get_rbac_status_dict()
        
        print(f"   Estado RBAC: {rbac_status.get('rbac_validation', 'unknown')}")
        if rbac_status.get('principal_id'):
            print(f"   Principal ID: {rbac_status['principal_id']}")
        if rbac_status.get('assigned_roles'):
            print(f"   Roles asignados: {len(rbac_status['assigned_roles'])}")
            for role in rbac_status['assigned_roles']:
                print(f"      ✅ {role['name']}")
        if rbac_status.get('missing_roles'):
            print(f"   Roles faltantes: {len(rbac_status['missing_roles'])}")
            for role in rbac_status['missing_roles']:
                print(f"      ❌ {role['name']}")
        if rbac_status.get('errors'):
            print(f"   Errores RBAC: {rbac_status['errors']}")
    except Exception as e:
        print(f"   ⚠️ Error en validación RBAC: {e}")
    
    print()
    
    # Parte 1: Test de credential con diferentes métodos Y SCOPES
    print("1. TESTING CREDENTIALS WITH DIFFERENT SCOPES...")
    
    # Test diferentes scopes para Azure Search
    scopes_to_test = [
        "https://search.azure.com/.default",
        "https://cognitiveservices.azure.com/.default",
        "https://management.azure.com/.default"
    ]
    
    for scope in scopes_to_test:
        print(f"   Testing scope: {scope}")
        try:
            default_cred = DefaultAzureCredential()
            token = await default_cred.get_token(scope)
            print(f"      ✅ Token obtenido: {token.token[:20]}...")
            await default_cred.close()
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    print()
    
    # Parte 2: Test directo con REST API usando diferentes scopes
    print("2. TESTING REST API ACCESS WITH DIFFERENT SCOPES...")
    
    for scope in scopes_to_test:
        print(f"   Testing REST API with scope: {scope}")
        try:
            # Obtener token para REST
            cred = DefaultAzureCredential()
            token = await cred.get_token(scope)
            
            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json"
            }
            
            # Test simple: Get index info
            url = f"{endpoint}/indexes/{search_index}?api-version=2023-11-01"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    print(f"      Status: {response.status}")
                    
                    if response.status == 200:
                        print(f"      ✅ Acceso exitoso con scope {scope}")
                        data = await response.json()
                        print(f"      Index name: {data.get('name', 'N/A')}")
                        break  # Si funciona, no necesitamos probar otros scopes
                    elif response.status == 403:
                        print(f"      ❌ Error 403 (Forbidden) con scope {scope}")
                        error_text = await response.text()
                        print(f"      Error: {error_text[:200]}")
                    else:
                        print(f"      ❌ Error HTTP {response.status} con scope {scope}")
                        error_text = await response.text()
                        print(f"      Error: {error_text[:200]}")
            
            await cred.close()
            
        except Exception as e:
            print(f"      ❌ Exception con scope {scope}: {e}")
    
    print()
    
    # Parte 3: Test directo con SearchClient (mismo flujo que la app)
    print("3. TESTING SEARCHCLIENT DIRECTLY...")
    
    try:
        # Usar exactamente la misma configuración que la app
        credential = DefaultAzureCredential()
        search_client = SearchClient(
            endpoint=endpoint,
            index_name=search_index,
            credential=credential  # SearchClient maneja el scope internamente
        )
        
        # Intentar obtener document count
        result = await search_client.get_document_count()
        print(f"   ✅ SearchClient funcionando. Document count: {result}")
        
        await search_client.close()
        await credential.close()
        
    except ClientAuthenticationError as e:
        print(f"   ❌ Authentication Error: {e}")
        print(f"   Error code: {e.error_code if hasattr(e, 'error_code') else 'N/A'}")
    except HttpResponseError as e:
        print(f"   ❌ HTTP Response Error: {e}")
        print(f"   Status: {e.status_code}")
        print(f"   Message: {e.message}")
        print(f"   Error code: {e.error_code if hasattr(e, 'error_code') else 'N/A'}")
    except Exception as e:
        print(f"   ❌ Exception en SearchClient: {e}")
        traceback.print_exc()
    
    print()
    
    # Parte 4: Test de operaciones específicas
    print("4. TESTING SPECIFIC OPERATIONS...")
    
    try:
        credential = DefaultAzureCredential()
        search_client = SearchClient(
            endpoint=endpoint,
            index_name=search_index,
            credential=credential
        )
        
        # Test 1: Simple search
        try:
            results = await search_client.search(search_text="*", top=1)
            docs = []
            async for doc in results:
                docs.append(doc)
            print(f"   ✅ Search operation: {len(docs)} documents")
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
        
        await search_client.close()
        await credential.close()
        
    except Exception as e:
        print(f"   ❌ Exception en operations test: {e}")
    
    print()
    print("=== FIN DIAGNÓSTICO ===")


if __name__ == "__main__":
    asyncio.run(detailed_search_diagnosis())
