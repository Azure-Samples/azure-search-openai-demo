# SharePoint Configuration Guide

Este sistema permite configurar dinámicamente qué carpetas y sitios buscar en SharePoint sin necesidad de hardcodear valores específicos del cliente.

## Estructura de Configuración

### 1. Archivo JSON Base (`sharepoint_config.json`)
Contiene la configuración por defecto que se aplicará a todos los deployments:

```json
{
  "search_folders": ["Pilotos", "Pilots", "Documents", "Documentos"],
  "site_keywords": ["company", "general", "operativ", "pilot"],
  "file_extensions": [".pdf", ".doc", ".docx"],
  "max_sites_to_search": 15,
  "search_depth": 5,
  "fallback_to_content_search": true,
  "search_queries": ["pilotos", "pilots", "documentos"]
}
```

### 2. Archivo de Entorno Específico (`.env`)
Permite sobrescribir la configuración base para deployments específicos.

## Variables de Configuración

### Carpetas de Búsqueda
```bash
SHAREPOINT_SEARCH_FOLDERS=Pilotos,Pilots,Documents,Documentos
```
Lista de nombres de carpetas a buscar en orden de prioridad.

### Keywords de Sitios
```bash
SHAREPOINT_SITE_KEYWORDS=company,general,operativ,pilot,flight,vuelo
```
Palabras clave para identificar sitios relevantes de SharePoint/Teams.

### Queries de Búsqueda
```bash
SHAREPOINT_SEARCH_QUERIES=pilotos,pilots,documentos,documents
```
Términos para búsqueda de contenido cuando no se encuentran carpetas específicas.

### Configuraciones Numéricas
```bash
SHAREPOINT_MAX_SITES=15          # Máximo número de sitios a explorar
SHAREPOINT_SEARCH_DEPTH=5        # Profundidad máxima de búsqueda recursiva
```

### Configuraciones Booleanas
```bash
SHAREPOINT_ENABLE_CONTENT_FALLBACK=true  # Habilitar búsqueda por contenido
```

### Extensiones de Archivo
```bash
SHAREPOINT_FILE_EXTENSIONS=.pdf,.doc,.docx,.xls,.xlsx
```

## Deployments Específicos

### Para Volaris/Pilotos
```bash
# Usar archivo de configuración específico
cp config/sharepoint_volaris.env config/sharepoint.env
```

### Para Recursos Humanos
```bash
# Usar archivo de configuración específico
cp config/sharepoint_hr.env config/sharepoint.env
```

### Para Cliente Personalizado
1. Copiar un archivo de configuración existente:
   ```bash
   cp config/sharepoint_volaris.env config/sharepoint_cliente.env
   ```

2. Modificar las variables según las necesidades del cliente:
   ```bash
   # Ejemplo para una empresa de logística
   SHAREPOINT_SEARCH_FOLDERS=Logistics,Logistica,Operations,Operaciones
   SHAREPOINT_SITE_KEYWORDS=logistics,supply,chain,transport,warehouse
   SHAREPOINT_SEARCH_QUERIES=logistics,supply chain,transport,almacen
   ```

3. Activar la configuración:
   ```bash
   cp config/sharepoint_cliente.env config/sharepoint.env
   ```

## Uso en Código

### Obtener Archivos con Configuración Dinámica
```python
from core.graph import get_configured_files

# Buscar usando configuración actual
files = get_configured_files()
```

### Verificar Configuración Actual
```python
from core.graph import get_sharepoint_config_summary

# Obtener resumen de configuración
config = get_sharepoint_config_summary()
print(f"Carpetas configuradas: {config['search_folders']}")
```

### Debug de Configuración
```bash
# Verificar configuración actual
curl http://localhost:50505/debug/sharepoint/config

# Probar búsqueda con configuración actual
curl http://localhost:50505/debug/sharepoint/test-configured-folders
```

## Flujo de Búsqueda

1. **Filtrado de Sitios**: Identifica sitios relevantes usando `site_keywords`
2. **Búsqueda de Carpetas**: Busca cada carpeta en `search_folders` en orden de prioridad
3. **Búsqueda Recursiva**: Si no encuentra carpeta, busca recursivamente hasta `search_depth`
4. **Fallback de Contenido**: Si está habilitado, busca por contenido usando `search_queries`
5. **Filtrado de Archivos**: Prioriza archivos con extensiones en `file_extensions`

## Beneficios

- ✅ **Sin Hardcoding**: No hay valores específicos del cliente en el código
- ✅ **Configuración Flexible**: Diferentes deployments con diferentes configuraciones
- ✅ **Fallback Inteligente**: Múltiples estrategias de búsqueda
- ✅ **Escalabilidad**: Control de límites para prevenir timeouts
- ✅ **Debug Fácil**: Endpoints para verificar configuración y resultados

## Migración desde Versión Anterior

La función legacy `get_pilotos_files()` sigue funcionando pero internamente usa la nueva configuración. Para migration completa:

```python
# Antes (hardcoded)
files = get_pilotos_files("DevOps")

# Ahora (configurable)
files = get_configured_files()
```
