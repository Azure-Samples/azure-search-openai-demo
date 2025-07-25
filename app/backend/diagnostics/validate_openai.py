"""
Validación de acceso a Azure OpenAI
"""

import os
try:
    from .utils_logger import log_ok, log_error, log_info
except ImportError:
    # Fallback para ejecución directa
    def log_ok(msg): print("✅ " + msg)
    def log_error(msg): print("❌ " + msg)
    def log_info(msg): print("🔍 " + msg)

def validate_openai_access():
    """Valida la configuración y acceso a Azure OpenAI"""
    log_info("[OPENAI] Validando configuración de Azure OpenAI...")
    
    # Variables requeridas para Azure OpenAI
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT",
        "AZURE_OPENAI_CHATGPT_MODEL",
        "AZURE_OPENAI_API_VERSION"
    ]
    
    # Variables opcionales
    optional_vars = [
        "AZURE_OPENAI_SERVICE",
        "AZURE_OPENAI_RESOURCE_GROUP",
        "AZURE_OPENAI_EMB_DEPLOYMENT",
        "AZURE_OPENAI_EMB_MODEL_NAME"
    ]
    
    all_good = True
    
    print("  Variables requeridas de OpenAI:")
    for var in required_vars:
        val = os.getenv(var)
        if val:
            # Mostrar solo los primeros caracteres de endpoints sensibles
            display_val = val if "ENDPOINT" not in var else val[:50] + "..."
            print(f"    {var}: ✅ {display_val}")
        else:
            print(f"    {var}: ❌ No definida")
            all_good = False
    
    print("  Variables opcionales:")
    for var in optional_vars:
        val = os.getenv(var)
        if val:
            print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ⚠️ No definida (opcional)")
    
    if not all_good:
        print("  OPENAI: ❌ Faltan variables requeridas")
        return 1
    
    # Intentar prueba de conectividad y autenticación
    try:
        print("  Probando autenticación...")
        from azure.identity import DefaultAzureCredential
        
        cred = DefaultAzureCredential()
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        print(f"    Token: ✅ Obtenido ({token.token[:20]}...)")
        
        # Intentar llamada básica al modelo
        print("  Probando llamada al modelo...")
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_ad_token_provider=lambda: cred.get_token("https://cognitiveservices.azure.com/.default").token
        )
        
        messages = [
            {"role": "system", "content": "Eres un asistente de validación técnica."},
            {"role": "user", "content": "Responde solo 'OK' para validar acceso."}
        ]
        
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT"),
            messages=messages,
            temperature=0.1,
            max_tokens=10
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"    Respuesta del modelo: ✅ '{response_text}'")
        print("  OPENAI: ✅ Configuración y acceso validados")
        return 0
        
    except Exception as e:
        print(f"    Error: ❌ {str(e)[:100]}")
        print("  OPENAI: ❌ Error en validación de acceso")
        return 1

if __name__ == "__main__":
    exit(validate_openai_access())

import os
try:
    from .utils_logger import log_ok, log_error, log_info
except ImportError:
    # Fallback para ejecución directa
    def log_ok(msg): print("✅ " + msg)
    def log_error(msg): print("❌ " + msg)
    def log_info(msg): print("🔍 " + msg)

def validate_openai_access():
    """Valida configuración y acceso a Azure OpenAI"""
    log_info("[OPENAI] Validando configuración de Azure OpenAI...")
    
    # Variables requeridas para Azure OpenAI
    required_vars = [
        "AZURE_OPENAI_SERVICE",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT",
        "AZURE_OPENAI_CHATGPT_MODEL",
        "AZURE_OPENAI_API_VERSION"
    ]
    
    # Variables opcionales
    optional_vars = [
        "AZURE_OPENAI_API_KEY_OVERRIDE",
        "AZURE_OPENAI_EMB_DEPLOYMENT",
        "AZURE_OPENAI_EMB_MODEL_NAME",
        "AZURE_OPENAI_REASONING_EFFORT"
    ]
    
    all_good = True
    
    print("  Variables requeridas:")
    for var in required_vars:
        val = os.getenv(var)
        if val:
            if "KEY" in var or "SECRET" in var:
                print(f"    {var}: ✅ {val[:10]}***")
            else:
                print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ❌ No definida")
            all_good = False
    
    print("  Variables opcionales:")
    for var in optional_vars:
        val = os.getenv(var)
        if val:
            if "KEY" in var or "SECRET" in var:
                print(f"    {var}: ✅ {val[:10]}***")
            else:
                print(f"    {var}: ✅ {val}")
        else:
            print(f"    {var}: ⚠️ No definida (opcional)")
    
    # Construir endpoint si es posible
    openai_service = os.getenv("AZURE_OPENAI_SERVICE")
    if openai_service:
        endpoint = f"https://{openai_service}.openai.azure.com/"
        print(f"    Endpoint calculado: {endpoint}")
    
    if all_good:
        print("  OPENAI: ✅ Configuración completa")
        return 0
    else:
        print("  OPENAI: ❌ Faltan variables requeridas")
        return 1

def test_openai_connection():
    """Prueba conexión real con Azure OpenAI"""
    try:
        from azure.identity import DefaultAzureCredential
        from openai import AzureOpenAI
        
        # Obtener configuración
        openai_service = os.getenv("AZURE_OPENAI_SERVICE")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        model = os.getenv("AZURE_OPENAI_CHATGPT_MODEL")
        
        if not all([openai_service, api_version, deployment, model]):
            print("    ❌ Variables de OpenAI no configuradas")
            return 1
        
        endpoint = f"https://{openai_service}.openai.azure.com/"
        
        # Verificar si usar API key o credential
        api_key = os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE")
        if api_key:
            print("    🔑 Usando API Key override")
            client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                api_key=api_key
            )
        else:
            print("    🔑 Usando DefaultAzureCredential")
            credential = DefaultAzureCredential()
            client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_ad_token_provider=lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token
            )
        
        # Hacer una llamada de prueba
        messages = [
            {"role": "system", "content": "Eres un asistente de validación técnica."},
            {"role": "user", "content": "Responde únicamente 'OK' para confirmar que funciona."}
        ]
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=10
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"    💬 Respuesta del modelo: {response_text}")
        print("    ✅ Conexión con Azure OpenAI exitosa")
        return 0
        
    except Exception as e:
        print(f"    ❌ Error conectando con Azure OpenAI: {str(e)}")
        return 1

if __name__ == "__main__":
    result = validate_openai_access()
    if result == 0:
        result = test_openai_connection()
    exit(result)
