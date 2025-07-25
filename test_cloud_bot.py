#!/usr/bin/env python3
import os
import argparse
import requests
import asyncio
from dotenv import load_dotenv
from azure.identity.aio import ManagedIdentityCredential
from azure.core.exceptions import ClientAuthenticationError

# 🧪 Cargar variables locales si existen
load_dotenv()

async def validate_mi_access(resource: str):
    """Valida el acceso del Managed Identity a un recurso específico"""
    try:
        credential = ManagedIdentityCredential()
        token = await credential.get_token(resource)
        print(f"🔑 Token adquirido correctamente para: {resource}")
        return True
    except ClientAuthenticationError as e:
        print(f"🚫 Error de autenticación con MI: {e.message}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado validando MI: {str(e)}")
        return False

async def test_azure_search_access():
    """Prueba específica del acceso a Azure Search con Managed Identity"""
    print("\n🔍 Validando acceso del Managed Identity a Azure Search...")
    
    # Recursos a probar
    resources_to_test = [
        "https://search.azure.com/",  # Azure Search scope
        "https://management.azure.com/",  # Azure Management scope
    ]
    
    results = []
    for resource in resources_to_test:
        print(f"\n🧪 Probando acceso a: {resource}")
        success = await validate_mi_access(resource)
        results.append(success)
    
    if all(results):
        print("✅ Managed Identity tiene acceso a todos los recursos necesarios")
        return True
    else:
        print("❌ Managed Identity no tiene acceso completo")
        return False

def check_env_vars(required=None):
    required = required or ["OPENAI_API_KEY", "AZURE_CLIENT_ID", "AZURE_TENANT_ID"]
    missing = [var for var in required if not os.getenv(var)]
    return missing

def detect_cloud_env():
    if "CODESPACES" in os.environ:
        return "Codespaces"
    if "GITHUB_ACTIONS" in os.environ:
        return "GitHub Actions"
    if os.environ.get("CONTAINER_APP_ENV", "").lower() == "true":
        return "Container Apps"
    return None

def test_cloud_bot(question, verbose=False):
    base_url = os.getenv("BOT_CLOUD_URL") or "https://api-volaris-dev-eus-001.whiteglacier-cc1b580c.eastus.azurecontainerapps.io"

    # 🔐 Validar Managed Identity (solo en ambiente cloud)
    cloud_env = detect_cloud_env()
    if cloud_env:
        print("\n🔐 Validando Managed Identity en ambiente cloud...")
        try:
            # Ejecutar validación asíncrona
            mi_success = asyncio.run(test_azure_search_access())
            if not mi_success:
                print("⚠️ Advertencia: Managed Identity puede tener problemas de acceso")
        except Exception as e:
            print(f"⚠️ No se pudo validar MI (puede ser normal en dev): {e}")

    # 1️⃣ Validar /debug/sharepoint/config
    try:
        print("\n🔍 Validando configuración desde /debug/sharepoint/config...")
        r = requests.get(f"{base_url}/debug/sharepoint/config", timeout=15)
        j = r.json()
        
        # La estructura correcta tiene config dentro del response
        config = j.get("config", {})
        status = j.get("status", "")
        
        assert config.get("authentication") == "success", f"Autenticación fallida - Status: {status}"
        assert status == "success", f"Status del endpoint no es success: {status}"

        drive_id = config.get("drive_id")
        site_id = config.get("site_id")
        files_found = int(config.get("files_found", 0))
        sample_files = config.get("sample_files", [])

        print(f"✅ Auth OK - Drive ID: {drive_id}")
        print(f"✅ Site ID: {site_id}")
        print(f"✅ Archivos encontrados: {files_found}")
        print(f"✅ Ejemplos: {sample_files[:2]}...")

        if files_found == 0:
            print("⚠️ Advertencia: SharePoint no devolvió archivos")
        
    except Exception as e:
        print(f"❌ Error en configuración inicial: {e}")
        return False

    # 2️⃣ Validar conectividad a /ask
    try:
        print(f"\n🌐 Probando endpoint /ask con pregunta: {question}")
        
        # Usar el formato correcto de la API
        test_message = {
            "messages": [{"role": "user", "content": question}],
            "stream": False,
            "context": {
                "overrides": {
                    "retrieval_mode": "hybrid",
                    "semantic_ranker": True,
                    "semantic_captions": True,
                    "top": 3,
                    "suggest_followup_questions": True
                }
            }
        }
        
        resp = requests.post(
            f"{base_url}/ask",
            json=test_message,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=60
        )
        status_code = resp.status_code
        headers = resp.headers
        
        if verbose:
            print(f"📊 Status Code: {status_code}")
            print("📬 Headers de respuesta:")
            for k, v in headers.items():
                print(f"   {k}: {v}")
        
        resp.raise_for_status()
        result = resp.json()
        
        # Extraer contenido de la respuesta
        content = result.get("message", {}).get("content", "")
        if content:
            print(f"✅ Status {status_code} - Respuesta del bot:")
            print(f"🧠 {content[:200]}...")
            
            # Mostrar datos adicionales si existen
            data_points = result.get("context", {}).get("data_points", [])
            if data_points:
                print(f"📚 Documentos consultados: {len(data_points)}")
                
            followups = result.get("context", {}).get("followup_questions", [])
            if followups:
                print(f"❓ Preguntas sugeridas: {len(followups)}")
            
            print("🎉 ¡Bot funcionando correctamente!")
            return True
        else:
            print("❌ Respuesta vacía del bot")
            return False
            
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        reason = getattr(e.response, "reason", "")
        print(f"❌ Error HTTP en /ask: status {status} ({reason})")
        
        if status == 403:
            print("🔒 Posible error de permisos en Azure Search - Verificar Managed Identity")
        elif status == 500:
            print("💥 Error interno - puede ser excepción en el servicio (Azure Search, payload, etc.)")
            # Mostrar más detalles del error si están disponibles
            try:
                error_details = e.response.json()
                print(f"� Detalles del error: {error_details}")
            except:
                print(f"📋 Error texto: {e.response.text}")
        elif status == 404:
            print("🔍 Endpoint no encontrado - verificar URL de la aplicación")
        elif status == 401:
            print("🔑 Error de autenticación - verificar configuración de identidad")
        
        return False
    except Exception as e:
        print(f"❌ Error inesperado al llamar a /ask: {e}")
        return False

# 🚀 Argumentos
parser = argparse.ArgumentParser(description="Probador pro del bot en la nube v3.0")
parser.add_argument("--cloud-only", action="store_true", help="Evita validaciones locales")
parser.add_argument("--verbose", action="store_true", help="Modo detallado")
parser.add_argument("--question", type=str, default="¿Qué información tienes sobre procedimientos de emergencia en vuelo?", help="Pregunta para el bot")
args = parser.parse_args()

if __name__ == "__main__":
    print("🚀 Probador Pro del Bot en la Nube v3.0")
    print("=" * 50)
    
    # 🔍 Diagnóstico
    cloud_env = detect_cloud_env()
    missing = check_env_vars()

    print("\n🔧 Entorno detectado:")
    print(f"   - Cloud: {cloud_env or 'Local/Dev Container'}")
    print(f"   - Modo: {'Cloud-only' if args.cloud_only else 'Local + Cloud'}")

    if args.cloud_only or cloud_env:
        if missing:
            print(f"\n⚠️ Variables locales faltantes: {missing}")
            print("ℹ️  Continuando - la aplicación en la nube tiene su propia configuración")
        print("\n🛰️ Ejecutando prueba directamente en entorno cloud...")
        success = test_cloud_bot(args.question, verbose=args.verbose)
    else:
        if missing:
            print(f"\n❌ Faltan variables requeridas: {missing}")
            print("💡 Usa --cloud-only para omitir validaciones locales")
            exit(1)
        print("\n🧪 Ejecutando prueba completa desde entorno local + cloud...")
        success = test_cloud_bot(args.question, verbose=args.verbose)
    
    print("\n" + "=" * 50)
    if success:
        print("🎯 ¡BOT COMPLETAMENTE FUNCIONAL EN LA NUBE!")
        exit(0)
    else:
        print("🔍 Revisar logs y configuración del bot")
        exit(1)