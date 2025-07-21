#!/bin/bash
# Script para ejecutar la aplicación en local con variables de entorno de desarrollo

# Cargar variables de entorno desde el archivo .env de desarrollo
export $(cat ../../.azure/dev/.env | grep -v '^#' | xargs)

# Configurar variables específicas para desarrollo local
export BACKEND_URI="http://localhost:8000"
export OPENAI_HOST="azure"

# Configurar variables de SharePoint para desarrollo local
export SHAREPOINT_SEARCH_FOLDERS="Pilotos,Pilots,Documents,Documentos"
export SHAREPOINT_SITE_KEYWORDS="company,general,operativ,pilot,flight,vuelo"
export SHAREPOINT_SEARCH_QUERIES="pilotos,pilots,documentos,documents"
export SHAREPOINT_MAX_SITES="15"
export SHAREPOINT_SEARCH_DEPTH="5"
export SHAREPOINT_ENABLE_CONTENT_FALLBACK="true"
export SHAREPOINT_FILE_EXTENSIONS=".pdf,.doc,.docx,.xls,.xlsx"

# Mostrar información de configuración
echo "=== Configuración de la aplicación ==="
echo "BACKEND_URI: $BACKEND_URI"
echo "AZURE_OPENAI_ENDPOINT: $AZURE_OPENAI_ENDPOINT"
echo "AZURE_SEARCH_SERVICE: $AZURE_SEARCH_SERVICE"
echo "AZURE_TENANT_ID: $AZURE_TENANT_ID"
echo "OPENAI_HOST: $OPENAI_HOST"
echo "=================================="

# Ejecutar la aplicación usando Quart
echo "Iniciando aplicación en http://localhost:8000"
/usr/local/bin/python -m quart --app app:create_app() --host 0.0.0.0 --port 8000 --debug run
