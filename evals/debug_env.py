import os
from dotenv import load_dotenv

load_dotenv()

def debug_env_variables():
    keys = [
        "AZURE_CLIENT_APP_ID",
        "AZURE_CLIENT_APP_SECRET",
        "AZURE_TENANT_ID",
        "SHAREPOINT_SITE_ID",
        "AZURE_DOCUMENTINTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY"
    ]
    
    print("\n🔍 Diagnóstico de variables de entorno:")
    for key in keys:
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: {value[:6]}... (ok)")
        else:
            print(f"❌ {key} no está definido")
    print("\n")

if __name__ == "__main__":
    debug_env_variables()