# Documentación de Configuración SharePoint

## Resumen
Se ha implementado un sistema completamente configurable para la integración con SharePoint que permite:
- Buscar en múltiples carpetas configurables (no solo "Pilotos")
- Filtrar sitios de SharePoint usando keywords configurables
- Deployments flexibles para diferentes clientes sin cambios de código
- Fallback a búsqueda de contenido cuando no se encuentran carpetas específicas

## Archivos de Configuración

### 1. Configuración Base JSON
**Archivo:** `app/backend/sharepoint_config/sharepoint_config.json`
```json
{
  "search_folders": ["Pilotos", "Pilots", "Documents", "Documentos", "Files", "Archivos"],
  "site_keywords": ["company", "general", "operativ", "pilot", "flight", "vuelo", "aviaci", "servic", "recurso", "human", "admin", "direcci"],
  "file_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"],
  "max_sites_to_search": 15,
  "search_depth": 5,
  "fallback_to_content_search": true,
  "search_queries": ["pilotos", "pilots", "documentos", "documents"]
}
```

### 2. Configuración Específica por Entorno
**Archivo:** `app/backend/sharepoint_config/sharepoint.env`

Variables de entorno que sobrescriben la configuración JSON:

```bash
# Carpetas principales a buscar (separadas por comas)
SHAREPOINT_SEARCH_FOLDERS=Pilotos,Pilots,Documents,Documentos

# Keywords para identificar sitios relevantes
SHAREPOINT_SITE_KEYWORDS=company,general,operativ,pilot,flight,vuelo,aviaci

# Queries para búsqueda de contenido como fallback
SHAREPOINT_SEARCH_QUERIES=pilotos,pilots,documentos,documents

# Límites de búsqueda
SHAREPOINT_MAX_SITES=15
SHAREPOINT_SEARCH_DEPTH=5

# Habilitar búsqueda de contenido como fallback
SHAREPOINT_ENABLE_CONTENT_FALLBACK=true

# Extensiones de archivo priorizadas
SHAREPOINT_FILE_EXTENSIONS=.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt
```

### 3. Configuraciones Pre-configuradas por Cliente

#### Para Volaris/Pilotos
**Archivo:** `app/backend/sharepoint_config/sharepoint_volaris.env`
```bash
SHAREPOINT_SEARCH_FOLDERS=Pilotos,Pilots,Documents,Documentos,Files,Archivos
SHAREPOINT_SITE_KEYWORDS=company,general,operativ,pilot,flight,vuelo,aviaci,servic,recurso,human,admin,direcci,volaris,aeronaut
SHAREPOINT_SEARCH_QUERIES=pilotos,pilots,documentos,documents,volaris,flight,aviation
```

#### Para Recursos Humanos
**Archivo:** `app/backend/sharepoint_config/sharepoint_hr.env`
```bash
SHAREPOINT_SEARCH_FOLDERS=HR,Human Resources,Recursos Humanos,Documents,Documentos,Policies,Politicas
SHAREPOINT_SITE_KEYWORDS=human,resources,hr,recurso,admin,policy,politica,employee,empleado,personal
SHAREPOINT_SEARCH_QUERIES=hr,recursos humanos,human resources,policies,empleados,personal
SHAREPOINT_MAX_SITES=10
SHAREPOINT_SEARCH_DEPTH=3
```

## Configuración de Conexión SharePoint

### Variables de Entorno Requeridas
```bash
# Autenticación Azure AD
AZURE_TENANT_ID=tu-tenant-id
AZURE_CLIENT_APP_ID=tu-client-app-id
AZURE_CLIENT_APP_SECRET=tu-client-app-secret
```

### Permisos Requeridos en Azure AD
La aplicación necesita los siguientes permisos de Microsoft Graph:
- `Sites.Read.All` - Leer sitios de SharePoint
- `Files.Read.All` - Leer archivos
- `Group.Read.All` - Leer grupos de Teams (para sitios de Teams)

## Cómo Usar para Diferentes Deployments

### Opción 1: Variables de Entorno
Para un deployment específico, copia y modifica uno de los archivos .env:
```bash
cp sharepoint_config/sharepoint_hr.env sharepoint_config/sharepoint_cliente.env
# Editar sharepoint_cliente.env con configuración específica
# Cargar en el entorno antes de ejecutar la aplicación
source sharepoint_config/sharepoint_cliente.env
```

### Opción 2: Modificar JSON Base
Para cambios permanentes, edita el archivo JSON:
```bash
# Editar sharepoint_config/sharepoint_config.json
# Cambiar search_folders, site_keywords, etc.
```

### Opción 3: Múltiples Archivos de Configuración
Crea archivos específicos por cliente y selecciona dinámicamente:
```python
# En código Python, especificar archivo de configuración
from sharepoint_config.sharepoint_config import SharePointConfig
config = SharePointConfig(env_file="sharepoint_config/sharepoint_cliente.env")
```

## Funcionalidad Implementada

### 1. Búsqueda Dinámica en Sitios de Teams
- Busca automáticamente en todos los sitios de Teams disponibles
- Filtra sitios usando keywords configurables
- Prioriza sitios que probablemente contengan documentos relevantes

### 2. Búsqueda en Múltiples Carpetas
- Busca en orden de prioridad en las carpetas configuradas
- Soporta nombres en múltiples idiomas (Pilotos/Pilots, Documents/Documentos)
- Búsqueda recursiva configurable

### 3. Fallback Inteligente
- Si no encuentra carpetas específicas, usa búsqueda de contenido
- Queries de búsqueda configurables
- Limites configurables para evitar timeouts

### 4. Debugging y Monitoreo
- Endpoint `/debug/sharepoint/config` - Ver configuración actual
- Endpoint `/debug/sharepoint/test-configured-folders` - Probar búsqueda
- Logs detallados de qué sitios y carpetas se encuentran

## Endpoints de Debug

### Verificar Configuración
```bash
curl -X GET "http://localhost:50505/debug/sharepoint/config"
```

### Probar Búsqueda
```bash
curl -X GET "http://localhost:50505/debug/sharepoint/test-configured-folders"
```

### Buscar Archivo Específico
```bash
curl -X GET "http://localhost:50505/debug/sharepoint/find-file?filename=documento"
```

## Arquitectura de la Solución

### Archivos Principales
1. `core/graph.py` - Cliente principal de Microsoft Graph
2. `sharepoint_config/sharepoint_config.py` - Manejo de configuración
3. `sharepoint_config/sharepoint_config.json` - Configuración base
4. `sharepoint_config/*.env` - Configuraciones por cliente
5. `approaches/chatreadretrieveread.py` - Integración con chat

### Flujo de Búsqueda
1. Cargar configuración (JSON + variables de entorno)
2. Obtener sitios de SharePoint/Teams disponibles
3. Filtrar sitios usando keywords configuradas
4. Buscar en carpetas configuradas en orden de prioridad
5. Si no encuentra carpetas, usar búsqueda de contenido
6. Retornar resultados con metadatos de dónde se encontraron

## Beneficios de la Implementación

### ✅ Flexibilidad Total
- No hay código hardcodeado para carpetas o sitios específicos
- Configuración completa vía archivos externos
- Soporta múltiples idiomas y convenciones de nombres

### ✅ Deployments Fáciles
- Un solo codebase para múltiples clientes
- Configuración específica por cliente sin cambios de código
- Variables de entorno para configuración dinámica

### ✅ Robustez
- Fallback automático si no encuentra carpetas específicas
- Límites configurables para evitar timeouts
- Manejo de errores y logging detallado

### ✅ Escalabilidad
- Búsqueda eficiente en múltiples sitios
- Priorización inteligente de sitios relevantes
- Configuración de límites para rendimiento

## Próximos Pasos Recomendados

1. **Crear SharePoint de Prueba**: Como mencionaste, crear un nuevo SharePoint con documentos
2. **Configurar Permisos**: Asegurar que la app tenga permisos correctos
3. **Probar Configuraciones**: Usar diferentes archivos .env para diferentes escenarios
4. **Documentar por Cliente**: Crear guías específicas para cada tipo de deployment
5. **Automatizar Deployment**: Scripts para configurar diferentes entornos automáticamente
