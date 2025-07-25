"""
Validación de acceso a Azure OpenAI
"""

import os
import asyncio
import subprocess
import json

# Cargar variables de entorno automáticamente
try:
    from .env_loader import load_env_file
except ImportError:
    # Fallback para ejecución directa
    import sys
    sys.path.append(os.path.dirname(__file__))
    from env_loader import load_env_file

try:
    from .utils_logger import log_ok, log_error, log_info, log_warning
except ImportError:
    # Fallback para ejecución directa
    def log_ok(msg): print("✅ " + msg)
    def log_error(msg): print("❌ " + msg)
    def log_info(msg): print("🔍 " + msg)
    def log_warning(msg): print("⚠️ " + msg)

def check_disable_local_auth():
    """Verifica si disableLocalAuth está habilitado en Azure OpenAI"""
    try:
        openai_service = os.getenv("AZURE_OPENAI_SERVICE")
        resource_group = os.getenv("AZURE_RESOURCE_GROUP") or os.getenv("AZURE_OPENAI_RESOURCE_GROUP")
        
        if not openai_service or not resource_group:
            log_warning("No se puede verificar disableLocalAuth: faltan variables de servicio")
            return None
            
        # Ejecutar comando az para verificar disableLocalAuth
        cmd = [
            "az", "cognitiveservices", "account", "show",
            "--name", openai_service,
            "--resource-group", resource_group,
            "--query", "properties.disableLocalAuth",
            "--output", "tsv"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            disable_local_auth = result.stdout.strip().lower() == "true"
            return disable_local_auth
        else:
            log_warning(f"Error verificando disableLocalAuth: {result.stderr}")
            return None
            
    except Exception as e:
        log_warning(f"No se pudo verificar disableLocalAuth: {e}")
        return None

def validate_auth_strategy():
    """Valida la estrategia de autenticación (API key vs Managed Identity)"""
    log_info("Validando estrategia de autenticación...")
    
    # Verificar si hay API key configurada
    api_key = os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE")
    has_api_key = bool(api_key)
    
    # Verificar si hay Managed Identity configurada
    client_id = os.getenv("AZURE_CLIENT_ID")
    has_managed_identity = bool(client_id)
    
    # Verificar disableLocalAuth
    disable_local_auth = check_disable_local_auth()
    
    print("  Configuración de autenticación:")
    if has_api_key:
        masked_key = api_key[:10] + "***" if len(api_key) > 10 else "***"
        print(f"    AZURE_OPENAI_API_KEY_OVERRIDE: ✅ {masked_key}")
    else:
        print(f"    AZURE_OPENAI_API_KEY_OVERRIDE: ❌ No configurada")
    
    if has_managed_identity:
        print(f"    AZURE_CLIENT_ID: ✅ {client_id}")
    else:
        print(f"    AZURE_CLIENT_ID: ❌ No configurada")
    
    if disable_local_auth is not None:
        status = "🔒 DESHABILITADAS" if disable_local_auth else "🔑 HABILITADAS"
        print(f"    disableLocalAuth: {status}")
    else:
        print(f"    disableLocalAuth: ⚠️ No se pudo verificar")
    
    # Análisis de compatibilidad
    print("  Análisis de compatibilidad:")
    
    if disable_local_auth is True:
        if has_api_key and not has_managed_identity:
            log_error("❌ CONFLICTO: API key configurada pero disableLocalAuth=true (solo acepta Managed Identity)")
            return False
        elif has_api_key and has_managed_identity:
            log_warning("⚠️ API key será IGNORADA porque disableLocalAuth=true, usará Managed Identity")
        elif not has_api_key and has_managed_identity:
            log_ok("✅ Configuración correcta: Managed Identity con disableLocalAuth=true")
        else:
            log_error("❌ Sin autenticación válida: disableLocalAuth=true requiere Managed Identity")
            return False
    elif disable_local_auth is False:
        if has_api_key:
            log_ok("✅ Configuración válida: API key con disableLocalAuth=false")
        elif has_managed_identity:
            log_ok("✅ Configuración válida: Managed Identity con disableLocalAuth=false")
        else:
            log_error("❌ Sin autenticación configurada")
            return False
    else:
        log_warning("⚠️ No se pudo verificar disableLocalAuth, validación limitada")
        if not has_api_key and not has_managed_identity:
            log_error("❌ Sin autenticación configurada")
            return False
    
    return True

def validate_openai_access():
    """Valida la configuración y acceso a Azure OpenAI"""
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
            # Mostrar valor parcial para variables sensibles
            display_val = val if len(val) < 50 else val[:20] + "..."
            print(f"    {var}: ✅ {display_val}")
        else:
            print(f"    {var}: ❌ No definida")
            all_good = False
    
    print("  Variables opcionales:")
    for var in optional_vars:
        val = os.getenv(var)
        if val:
            if "API_KEY" in var:
                display_val = val[:10] + "***" if len(val) > 10 else "***"
            else:
                display_val = val
            print(f"    {var}: ✅ {display_val}")
        else:
            if var == "AZURE_OPENAI_API_KEY_OVERRIDE":
                # Mensaje especial para la API key
                is_production = os.getenv("RUNNING_IN_PRODUCTION", "false").lower() == "true"
                if is_production:
                    print(f"    {var}: ✅ No definida (PRODUCCIÓN usa Managed Identity - correcto)")
                else:
                    print(f"    {var}: ⚠️ No definida (local puede usar API key, ⚠️ CUIDADO: interferirá con producción si se mezcla)")
            else:
                print(f"    {var}: ⚠️ No definida (opcional)")
    
    # Calcular endpoint si es necesario
    openai_service = os.getenv("AZURE_OPENAI_SERVICE")
    if openai_service:
        endpoint = f"https://{openai_service}.openai.azure.com/"
        print(f"    Endpoint calculado: {endpoint}")
    
    print("")
    
    # **NUEVA VALIDACIÓN: Estrategia de autenticación**
    auth_valid = validate_auth_strategy()
    
    if not auth_valid:
        all_good = False
    
    if all_good:
        log_ok("OPENAI: ✅ Configuración completa")
    else:
        log_error("OPENAI: ❌ Faltan variables requeridas o hay conflictos de configuración")
    
    return all_good


def validate_openai_advanced():
    """Validación avanzada incluyendo prueba de conexión real"""
    # Variables requeridas para validación avanzada
    required_vars = [
        "AZURE_OPENAI_SERVICE",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT", 
        "AZURE_OPENAI_CHATGPT_MODEL",
        "AZURE_OPENAI_API_VERSION"
    ]
    
    optional_vars = [
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
