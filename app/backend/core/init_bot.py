import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential

def init_bot_context():
    errors = []

    # SharePoint / Graph credentials
    required_env = [
        "AZURE_CLIENT_APP_ID",
        "AZURE_CLIENT_APP_SECRET",
        "AZURE_TENANT_ID",
        "SHAREPOINT_SITE_ID"
    ]

    for var in required_env:
        if not os.getenv(var):
            errors.append(f"❌ Falta variable: {var}")
    
    # Azure OpenAI validation
    openai_api_key = os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE")
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")

    if not openai_api_key and not os.getenv("AZURE_MANAGED_CLIENT_ID"):
        errors.append("❌ OpenAI no tiene API Key ni Managed Identity definida")
    if not openai_endpoint:
        errors.append("❌ Falta AZURE_OPENAI_ENDPOINT")
    if not openai_deployment:
        errors.append("❌ Falta AZURE_OPENAI_CHATGPT_DEPLOYMENT")

    if errors:
        print("🚨 Errores críticos al iniciar el bot:")
        for err in errors:
            print(err)
        raise EnvironmentError("🛑 Entorno del bot incompleto. Verifica tus variables.")
    else:
        print("✅ Entorno del bot validado. Listo para despegar.")

    # Muestra tipo de credencial utilizada
    if openai_api_key:
        print("🔐 Usando API Key para Azure OpenAI")
    else:
        print("🔐 Usando Managed Identity para Azure OpenAI")

    # Validar credencial Graph
    graph_cred = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_APP_ID"),
        client_secret=os.getenv("AZURE_CLIENT_APP_SECRET")
    )
    print(f"🔧 Credencial Graph inicializada: {type(graph_cred)}")

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
    
    print("✅ Servicios básicos están operativos")
    return True
