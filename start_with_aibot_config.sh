#!/bin/bash

# Script para arrancar la aplicación con configuración específica de AIBot

echo "🚀 Arrancando aplicación con configuración AIBot..."

# Cargar configuración específica
source app/backend/sharepoint_config/sharepoint_aibot.env

echo "✅ Configuración cargada:"
echo "   Carpetas: $SHAREPOINT_SEARCH_FOLDERS"
echo "   Keywords: $SHAREPOINT_SITE_KEYWORDS"

# Arrancar aplicación
cd app && ./start.sh
