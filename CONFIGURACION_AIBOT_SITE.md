# Configuración para tu sitio AIBotProjectAutomation

## Para usar tu sitio específico (`https://lumston.sharepoint.com/sites/AIBotProjectAutomation/`):

### Opción 1: Script automático (RECOMENDADO)
```bash
# Desde la raíz del proyecto, ejecuta:
./start_with_aibot_config.sh
```

### Opción 2: Manual
```bash
# 1. Cargar configuración específica:
source app/backend/sharepoint_config/sharepoint_aibot.env

# 2. Arrancar aplicación:
cd app && ./start.sh
```

### 3. Verificar que funciona:
```bash
# Verificar configuración (debería mostrar keywords de aibot)
curl -X GET "http://localhost:50505/debug/sharepoint/config" | jq '.config.site_keywords'

# Probar búsqueda
curl -X GET "http://localhost:50505/debug/sharepoint/test-configured-folders" | jq .
```

## Personalización adicional:

### Si tienes carpetas específicas en tu sitio:
Edita `app/backend/sharepoint_config/sharepoint_aibot.env` y cambia:
```bash
SHAREPOINT_SEARCH_FOLDERS="TuCarpetaEspecifica,Pilotos,Documents"
```

### Si quieres agregar más keywords para tu sitio:
```bash
SHAREPOINT_SITE_KEYWORDS="aibot,automation,project,tu-palabra-adicional"
```

## ¡Eso es todo! 
Solo modifica el archivo de configuración `sharepoint_aibot.env` y usa el script para arrancar.
