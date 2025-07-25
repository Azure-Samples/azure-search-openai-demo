#!/usr/bin/env python3
"""
Validador de configuración de Azure OpenAI + Search con Managed Identity
Prueba que todos los servicios funcionen correctamente con DefaultAzureCredential
"""

import os
import asyncio
import json
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AsyncAzureOpenAI

# Cargar variables de entorno
load_dotenv()


async def test_openai_chat_completion():
    """Prueba la conexión a Azure OpenAI con Managed Identity"""
    print("🤖 Probando Azure OpenAI...")
    try:
        # 🧩 Credencial y cliente
        credential = DefaultAzureCredential()
        
        # Obtener configuración del entorno
        service = os.getenv("AZURE_OPENAI_SERVICE", "oai-volaris-dev-eus-001")
        deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4.1-mini")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        # Crear cliente usando el patrón correcto del código existente
        from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential, get_bearer_token_provider
        
        azure_credential = AsyncDefaultAzureCredential()
        token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
        
        client = AsyncAzureOpenAI(
            api_version=api_version,
            azure_endpoint=f"https://{service}.openai.azure.com",
            azure_ad_token_provider=token_provider,
        )

        # 💬 Mensaje simulado
        messages = [
            {"role": "system", "content": "Eres un copiloto técnico muy preciso y amigable."},
            {"role": "user", "content": "¿Qué significa un error HttpResponseError en Azure?"}
        ]

        # 🚀 Llamada de prueba
        response = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )

        print("✅ Azure OpenAI - Completado correctamente")
        print(f"🎯 Service: {service}")
        print(f"🎯 Deployment: {deployment}")
        print(f"💬 Respuesta: {response.choices[0].message.content[:100]}...")
        return True

    except Exception as e:
        print("🔴 Azure OpenAI - Error al generar la respuesta")
        if hasattr(e, 'status_code'):
            print(f"🔍 HTTP Status: {e.status_code}")
        if hasattr(e, 'message'):
            print(f"📨 Error Message: {e.message}")
        print(f"📛 Tipo de error: {type(e)}")
        print(f"📚 Detalles: {str(e)}")
        return False


def test_azure_search():
    """Prueba la conexión a Azure Search con Managed Identity"""
    print("\n🔍 Probando Azure Search...")
    try:
        # 🧩 Credencial
        credential = DefaultAzureCredential()
        
        # Obtener configuración del entorno
        search_service = os.getenv("AZURE_SEARCH_SERVICE", "srch-volaris-dev-eus-001")
        
        # Primero, descubrir los índices disponibles
        index_client = SearchIndexClient(
            endpoint=f"https://{search_service}.search.windows.net",
            credential=credential
        )
        
        print(f"📋 Descubriendo índices en: {search_service}")
        indexes = list(index_client.list_indexes())
        
        if not indexes:
            print("❌ No se encontraron índices en el servicio")
            return False
        
        print(f"✅ Encontrados {len(indexes)} índices:")
        for idx in indexes:
            print(f"   - {idx.name}")
        
        # Usar el primer índice disponible para la prueba
        search_index = indexes[0].name
        print(f"🎯 Usando índice: {search_index}")
        
        # Crear cliente de búsqueda
        search_client = SearchClient(
            endpoint=f"https://{search_service}.search.windows.net",
            index_name=search_index,
            credential=credential
        )
        
        # 🚀 Prueba simple de búsqueda
        results = search_client.search("*", top=1)
        
        # Iterar resultados
        result_count = 0
        for result in results:
            result_count += 1
            break  # Solo necesitamos verificar que funcione
            
        print("✅ Azure Search - Conectado correctamente")
        print(f"🎯 Service: {search_service}")
        print(f"🎯 Index: {search_index}")
        print(f"📊 Prueba de búsqueda exitosa")
        return True
        
    except Exception as e:
        print("🔴 Azure Search - Error en la búsqueda")
        if hasattr(e, 'status_code'):
            print(f"🔍 HTTP Status: {e.status_code}")
        if hasattr(e, 'message'):
            print(f"📨 Error Message: {e.message}")
        print(f"📛 Tipo de error: {type(e)}")
        print(f"📚 Detalles: {str(e)}")
        return False


def test_sharepoint_integration():
    """Prueba la integración con SharePoint"""
    print("\n📁 Probando integración SharePoint...")
    try:
        # Intentar importar desde la ubicación correcta del backend
        import sys
        sys.path.append('/workspaces/azure-search-openai-demo/app/backend')
        
        from core.graph import get_sharepoint_config_summary
        
        result = get_sharepoint_config_summary()
        
        if result.get("authentication") == "success":
            print("✅ SharePoint - Conectado correctamente")
            print(f"📊 Archivos encontrados: {result.get('files_found', 0)}")
            if result.get('sample_files'):
                print(f"📄 Archivo de ejemplo: {result['sample_files'][0]}")
            return True
        else:
            print("🔴 SharePoint - Error en autenticación")
            print(f"📚 Error: {result.get('error', 'Desconocido')}")
            return False
            
    except ImportError as ie:
        print("🟡 SharePoint - Módulo no disponible desde este contexto")
        print(f"📚 Info: {str(ie)}")
        print("ℹ️  Esta prueba funciona mejor desde el contenedor de la aplicación")
        return None  # No es un fallo, solo no disponible
            
    except Exception as e:
        print("🔴 SharePoint - Error en la conexión")
        print(f"📛 Tipo de error: {type(e)}")
        print(f"📚 Detalles: {str(e)}")
        return False


async def run_all_tests():
    """Ejecuta todas las pruebas de validación"""
    print("🚀 Iniciando validación completa de configuración...")
    print("=" * 60)
    
    # Variables de entorno críticas
    print("\n📋 Variables de entorno:")
    critical_vars = [
        "AZURE_OPENAI_SERVICE",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT", 
        "AZURE_SEARCH_SERVICE",
        "AZURE_SEARCH_INDEX",
        "CLIENT_ID",
        "CLIENT_SECRET",
        "AZURE_TENANT_ID"
    ]
    
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            # Ocultar secretos
            if "SECRET" in var or "KEY" in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: No configurada")
    
    print("\n" + "=" * 60)
    
    # Ejecutar pruebas
    results = []
    
    # 1. Prueba OpenAI
    openai_result = await test_openai_chat_completion()
    results.append(("Azure OpenAI", openai_result))
    
    # 2. Prueba Azure Search
    search_result = test_azure_search()
    results.append(("Azure Search", search_result))
    
    # 3. Prueba SharePoint
    sharepoint_result = test_sharepoint_integration()
    results.append(("SharePoint", sharepoint_result))
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VALIDACIÓN:")
    print("=" * 60)
    
    all_passed = True
    for service, passed in results:
        if passed is True:
            status = "✅ PASS"
        elif passed is False:
            status = "❌ FAIL"
            all_passed = False
        else:  # passed is None (SharePoint not available)
            status = "🟡 SKIP"
        print(f"{status} {service}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ¡TODAS LAS PRUEBAS CRÍTICAS PASARON!")
        print("✅ El bot está listo para funcionar correctamente")
    else:
        print("⚠️  ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisa los errores anteriores para solucionar los problemas")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    # Ejecutar las pruebas
    result = asyncio.run(run_all_tests())
    exit(0 if result else 1)
