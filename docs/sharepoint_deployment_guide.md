# Guía Rápida de Deployment - SharePoint

## Cuando tengas tu nuevo SharePoint listo, sigue estos pasos:

### 1. Configurar Permisos en Azure AD
Tu aplicación necesita estos permisos en Microsoft Graph:
```
Sites.Read.All
Files.Read.All  
Group.Read.All
```

### 2. Actualizar Variables de Entorno
En tu archivo `.env` o variables del sistema:
```bash
AZURE_TENANT_ID=tu-tenant-id-aqui
AZURE_CLIENT_APP_ID=tu-client-id-aqui  
AZURE_CLIENT_APP_SECRET=tu-client-secret-aqui
```

### 3. Configurar Carpetas de Búsqueda
Edita `sharepoint_config/sharepoint.env` con las carpetas que creaste:
```bash
# Si creaste una carpeta llamada "MisDocumentos" por ejemplo:
SHAREPOINT_SEARCH_FOLDERS=MisDocumentos,Pilotos,Documents,Documentos

# Si tu sitio tiene un nombre específico, agrégalo a keywords:
SHAREPOINT_SITE_KEYWORDS=company,general,operativ,tu-sitio-nombre
```

### 4. Comandos de Prueba Rápida

#### Verificar configuración:
```bash
curl -X GET "http://localhost:50505/debug/sharepoint/config" | jq .
```

#### Probar búsqueda de documentos:
```bash
curl -X GET "http://localhost:50505/debug/sharepoint/test-configured-folders" | jq .
```

#### Buscar un archivo específico:
```bash
curl -X GET "http://localhost:50505/debug/sharepoint/find-file?filename=NOMBRE_DE_TU_ARCHIVO" | jq .
```

### 5. Probar Chat Integration
```bash
curl -X POST "http://localhost:50505/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"content": "¿Qué documentos tienes disponibles?", "role": "user"}],
    "stream": false,
    "context": {"overrides": {"use_sharepoint": true, "top": 5}}
  }'
```

### Troubleshooting Común

#### Si no encuentra documentos:
1. Verificar permisos de la app en Azure AD
2. Confirmar que el sitio es accesible con las credenciales
3. Revisar logs para ver qué sitios se están explorando
4. Ajustar `site_keywords` si el nombre de tu sitio es muy específico

#### Si encuentra el sitio pero no la carpeta:
1. Verificar que `SHAREPOINT_SEARCH_FOLDERS` incluye el nombre exacto
2. Habilitar `SHAREPOINT_ENABLE_CONTENT_FALLBACK=true` para búsqueda de contenido
3. Aumentar `SHAREPOINT_SEARCH_DEPTH` si la carpeta está anidada

#### Para ver logs detallados:
Los logs muestran exactamente qué sitios y carpetas está explorando la aplicación.

### Personalización por Cliente

Para crear una configuración específica para tu nuevo SharePoint:
```bash
# Copia la configuración base
cp sharepoint_config/sharepoint.env sharepoint_config/sharepoint_mi_cliente.env

# Edita con configuración específica
nano sharepoint_config/sharepoint_mi_cliente.env

# Carga la configuración específica
source sharepoint_config/sharepoint_mi_cliente.env
```

¡Todo está listo para cuando tengas tu SharePoint configurado! 🚀
