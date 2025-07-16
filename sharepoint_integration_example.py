"""
Ejemplo de uso del chatbot con integración de SharePoint

Este archivo demuestra cómo el chatbot ahora puede acceder a archivos 
de la carpeta "Pilotos" en SharePoint cuando el usuario hace preguntas 
relacionadas con pilotos de aerolíneas, aviación, vuelos, etc.
"""

# Ejemplos de preguntas que ahora activarán la búsqueda en SharePoint:

# 1. "¿Qué documentos para pilotos están disponibles?"
# 2. "Necesito información sobre certificaciones de pilotos"
# 3. "¿Hay manuales de vuelo para capitanes?"
# 4. "Muéstrame la documentación para tripulación"
# 5. "¿Qué entrenamientos tienen los aviadores?"

# El flujo funciona así:
# 1. El usuario hace una pregunta
# 2. El sistema detecta si contiene palabras clave relacionadas con pilotos de aerolíneas
# 3. Si es así, busca tanto en Azure AI Search como en SharePoint
# 4. Combina los resultados y los presenta al usuario
# 5. El usuario recibe información tanto de documentos indexados como de SharePoint

# Palabras clave que activan la búsqueda en SharePoint:
PILOT_KEYWORDS = [
    "piloto", "pilotos", "pilot", "pilots",
    "capitán", "capitan", "captain", "comandante",
    "aerolínea", "aerolinea", "airline", "aviación", "aviation",
    "vuelo", "vuelos", "flight", "flights",
    "cabina", "cockpit", "tripulación", "crew",
    "aviador", "aviadores", "aviator", "aviators",
    "licencia de piloto", "certificación", "entrenamiento",
    "instructor de vuelo", "flight instructor"
]

# Variables de entorno requeridas para SharePoint:
# AZURE_TENANT_ID - ID del tenant de Azure
# AZURE_CLIENT_APP_ID - ID de la aplicación registrada en Azure AD
# AZURE_CLIENT_APP_SECRET - Secret de la aplicación

print("Integración de SharePoint configurada exitosamente!")
print("El chatbot ahora puede acceder a documentos de la carpeta 'Pilotos' en SharePoint.")
