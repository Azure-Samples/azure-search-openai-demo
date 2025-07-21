#!/usr/bin/env python3
"""
Script simple para ejecutar la aplicación en local con variables de entorno
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
env_path = "/workspaces/azure-search-openai-demo/.azure/dev/.env"
load_dotenv(env_path)

print("=== VARIABLES DE ENTORNO CARGADAS ===")
print(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
print(f"AZURE_SEARCH_SERVICE: {os.getenv('AZURE_SEARCH_SERVICE')}")
print(f"AZURE_TENANT_ID: {os.getenv('AZURE_TENANT_ID')}")
print(f"AZURE_CLIENT_APP_ID: {os.getenv('AZURE_CLIENT_APP_ID')}")
print("==========================================")

# Ejecutar la aplicación
if __name__ == "__main__":
    from main import app
    app.run(host="0.0.0.0", port=8000, debug=True)
