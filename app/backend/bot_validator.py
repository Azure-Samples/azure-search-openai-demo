"""
Bot Context Validator
Validador de entorno para el bot de Azure Search + OpenAI embebido
"""
import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential

def init_bot_context():
    """
    Validar el entorno completo del bot antes de inicialización.
    Verifica credenciales, variables de entorno y configuraciones críticas.
    """
    errors = []
    warnings = []

    print("🚀 Iniciando validación del entorno del bot...")

    # SharePoint / Graph credentials
    required_env = [
        "AZURE_CLIENT_APP_ID",
        "AZURE_CLIENT_APP_SECRET", 
        "AZURE_TENANT_ID",
        "SHAREPOINT_SITE_ID",
        "SITE_ID",
        "DRIVE_ID"
    ]

    for var in required_env:
        if not os.getenv(var):
            errors.append(f"❌ Falta variable: {var}")

    # Azure OpenAI validation
    openai_api_key = os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE")
    openai_service = os.getenv("AZURE_OPENAI_SERVICE")
    openai_deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not openai_api_key and not os.getenv("AZURE_CLIENT_ID"):
        errors.append("❌ OpenAI no tiene API Key ni Managed Identity definida")
    if not openai_service:
        errors.append("❌ Falta AZURE_OPENAI_SERVICE")
    if not openai_deployment:
        errors.append("❌ Falta AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    if not openai_api_version:
        errors.append("❌ Falta AZURE_OPENAI_API_VERSION")

    # Azure Search validation
    search_service = os.getenv("AZURE_SEARCH_SERVICE")
    search_index = os.getenv("AZURE_SEARCH_INDEX")
    if not search_service:
        errors.append("❌ Falta AZURE_SEARCH_SERVICE")
    if not search_index:
        errors.append("❌ Falta AZURE_SEARCH_INDEX")

    # Validar configuración de bot embebido
    azure_use_auth = os.getenv("AZURE_USE_AUTHENTICATION", "").lower()
    azure_unauth_access = os.getenv("AZURE_ENABLE_UNAUTHENTICATED_ACCESS", "").lower()
    
    if azure_use_auth == "true":
        warnings.append("⚠️  AZURE_USE_AUTHENTICATION=True - Bot requerirá login")
    if azure_unauth_access != "true":
        warnings.append("⚠️  AZURE_ENABLE_UNAUTHENTICATED_ACCESS!=True - Bot puede bloquear usuarios sin token")

    # Validar valores problemáticos
    drive_id = os.getenv("DRIVE_ID", "")
    if "\\" in drive_id:
        errors.append("❌ DRIVE_ID contiene backslashes (\\) - debe usar formato URL encoded")

    if errors:
        print("🚨 Errores críticos al iniciar el bot:")
        for err in errors:
            print(err)
        raise EnvironmentError("🛑 Entorno del bot incompleto. Verifica tus variables.")
    
    if warnings:
        print("⚠️  Advertencias de configuración:")
        for warn in warnings:
            print(warn)

    print("✅ Entorno del bot validado. Listo para despegar.")

    # Muestra tipo de credencial utilizada para OpenAI
    if openai_api_key:
        print(f"🔐 Usando API Key para Azure OpenAI (Service: {openai_service})")
        print(f"🎯 Deployment: {openai_deployment}")
    else:
        print("🔐 Usando Managed Identity para Azure OpenAI")

    # Validar credencial Graph
    try:
        graph_cred = ClientSecretCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_APP_ID"),
            client_secret=os.getenv("AZURE_CLIENT_APP_SECRET")
        )
        print(f"🔧 Credencial Graph inicializada: {type(graph_cred).__name__}")
    except Exception as e:
        print(f"❌ Error inicializando credencial Graph: {e}")
        raise

    # Mostrar resumen de configuración
    print("\n📋 Resumen de configuración:")
    print(f"   🏢 Tenant: {os.getenv('AZURE_TENANT_ID')}")
    print(f"   📁 SharePoint Site: {os.getenv('SHAREPOINT_SITE_ID')}")
    print(f"   🔍 Search Index: {search_index}")
    print(f"   🤖 OpenAI Service: {openai_service}")
    print(f"   🚪 Bot embebido: Sin autenticación requerida" if azure_unauth_access == "true" else "   🔐 Bot con autenticación")

    return True

def validate_runtime_status():
    """
    Validar el estado del bot en tiempo de ejecución.
    Verifica conectividad y permisos de servicios.
    """
    print("🔍 Validando estado de servicios en tiempo real...")
    
    # Test SharePoint connectivity
    try:
        from core.graph import get_access_token
        token = get_access_token()
        print("✅ SharePoint/Graph: Conectado correctamente")
    except Exception as e:
        print(f"❌ SharePoint/Graph: Error de conexión - {e}")
        return False
    
    # Test Azure Search connectivity  
    try:
        from azure.search.documents import SearchClient
        from core.azure_credential import get_azure_credential
        
        credential = get_azure_credential()
        search_client = SearchClient(
            endpoint=f"https://{os.getenv('AZURE_SEARCH_SERVICE')}.search.windows.net",
            index_name=os.getenv('AZURE_SEARCH_INDEX'),
            credential=credential
        )
        # Simple test query
        results = search_client.search("*", top=1)
        print("✅ Azure Search: Conectado correctamente") 
    except Exception as e:
        print(f"❌ Azure Search: Error de conexión - {e}")
        return False

    print("✅ Todos los servicios están operativos")
    return True

if __name__ == "__main__":
    # Test standalone
    init_bot_context()
    validate_runtime_status()
