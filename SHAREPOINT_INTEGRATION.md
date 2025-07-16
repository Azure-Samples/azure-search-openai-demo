# Integración de SharePoint con el Chatbot

## Descripción

Se ha integrado la funcionalidad de SharePoint al chatbot para permitir el acceso automático a documentos almacenados en la carpeta "Pilotos" de SharePoint cuando los usuarios hacen preguntas relacionadas con pilotos de aerolíneas, aviación, vuelos, tripulación, etc.

## Funcionalidad

### Detección Automática
El sistema detecta automáticamente cuando una consulta está relacionada con pilotos de aerolíneas utilizando palabras clave como:
- piloto, pilotos, pilot, pilots
- capitán, capitan, captain, comandante
- aerolínea, aerolinea, airline, aviación, aviation
- vuelo, vuelos, flight, flights
- cabina, cockpit, tripulación, crew
- aviador, aviadores, aviator, aviators
- licencia de piloto, certificación, entrenamiento
- instructor de vuelo, flight instructor

### Búsqueda Híbrida
Cuando se detecta una consulta relacionada con pilotos de aerolíneas, el sistema:
1. Realiza la búsqueda normal en Azure AI Search
2. Simultáneamente busca en la carpeta "Pilotos" de SharePoint
3. Combina ambos resultados para proporcionar una respuesta completa

## Archivos Modificados

### Nuevos Archivos
- `app/backend/core/graph.py` - Cliente de Microsoft Graph para acceso a SharePoint

### Archivos Modificados
- `app/backend/approaches/chatreadretrieveread.py` - Integración de SharePoint en el flujo de chat
- `app/backend/app.py` - Inicialización del cliente de SharePoint
- `tests/test_chatapproach.py` - Actualización de tests para incluir el nuevo parámetro

## Configuración Requerida

### Variables de Entorno
```
AZURE_TENANT_ID=<tu-tenant-id>
AZURE_CLIENT_APP_ID=<tu-application-id>
AZURE_CLIENT_APP_SECRET=<tu-application-secret>
```

### Configuración en Azure AD
1. Registrar una aplicación en Azure AD
2. Configurar permisos de Microsoft Graph:
   - `Sites.Read.All` - Para leer sitios de SharePoint
   - `Files.Read.All` - Para leer archivos
3. Generar un secreto de cliente
4. Configurar las variables de entorno

### Configuración de SharePoint
1. Tener acceso al sitio de SharePoint
2. Asegurar que existe una carpeta llamada "Pilotos" con documentos para pilotos de aerolíneas
3. Configurar permisos apropiados para la aplicación

## Uso

### Ejemplos de Consultas que Activan SharePoint
- "¿Qué documentos para pilotos están disponibles?"
- "Necesito información sobre certificaciones de pilotos"
- "¿Hay manuales de vuelo para capitanes?"
- "Muéstrame la documentación para tripulación"
- "¿Qué entrenamientos tienen los aviadores?"
- "¿Cómo renovar la licencia de piloto?"
- "Procedimientos de cabina para comandantes"

### Formato de Respuesta
El chatbot incluirá en sus respuestas:
- Resultados de Azure AI Search (documentos indexados)
- Documentos de SharePoint con la etiqueta "SharePoint: [nombre-archivo]"
- URLs directos a los archivos de SharePoint cuando estén disponibles

## Método de Integración

### Nuevos Métodos en ChatReadRetrieveReadApproach
- `_is_pilot_related_query()` - Detecta consultas relacionadas con pilotos de aerolíneas
- `_search_sharepoint_files()` - Busca archivos en SharePoint
- `_combine_search_results()` - Combina resultados de ambas fuentes

### Flujo de Ejecución
1. El usuario envía una pregunta
2. Se genera una consulta optimizada usando OpenAI
3. Se busca en Azure AI Search
4. Si la consulta es relacionada con pilotos de aerolíneas, también se busca en SharePoint
5. Los resultados se combinan y se envían a OpenAI para generar la respuesta

## Manejo de Errores

- Si SharePoint no está disponible, el sistema continúa funcionando solo con Azure AI Search
- Los errores de autenticación se manejan silenciosamente para no interrumpir el flujo
- Se implementa logging para monitorear el uso y detectar problemas

## Consideraciones de Rendimiento

- La búsqueda en SharePoint se ejecuta en paralelo con Azure AI Search
- Se limita el número de documentos recuperados de SharePoint (por defecto 3)
- Se trunca el contenido de archivos grandes para evitar exceder límites de tokens

## Próximos Pasos

1. Configurar las variables de entorno según tu ambiente
2. Probar la funcionalidad con preguntas relacionadas con pilotos de aerolíneas
3. Monitorear los logs para asegurar el correcto funcionamiento
4. Expandir las palabras clave si es necesario para incluir más términos de aviación específicos de tu caso de uso
