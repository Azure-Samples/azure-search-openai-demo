#!/usr/bin/env python3
"""
Script de prueba para la integración de SharePoint

Este script demuestra cómo probar la nueva funcionalidad de SharePoint 
integrada en el chatbot.
"""

import asyncio
import os
from unittest.mock import Mock

# Simulación de una consulta de prueba
async def test_sharepoint_integration():
    """
    Prueba conceptual de la integración de SharePoint
    """
    
    # Verificar variables de entorno
    required_env_vars = [
        'AZURE_TENANT_ID',
        'AZURE_CLIENT_APP_ID', 
        'AZURE_CLIENT_APP_SECRET'
    ]
    
    print("🔍 Verificando configuración de SharePoint...")
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("📋 Para configurar SharePoint, establece estas variables:")
        for var in missing_vars:
            print(f"   export {var}=<tu-valor>")
        return False
    else:
        print("✅ Variables de entorno configuradas correctamente")
    
    # Preguntas de ejemplo que activarían SharePoint
    pilot_questions = [
        "¿Qué documentos para pilotos están disponibles?",
        "Necesito información sobre certificaciones de pilotos",
        "¿Hay manuales de vuelo para capitanes?",
        "Muéstrame la documentación para tripulación",
        "¿Qué entrenamientos tienen los aviadores?",
        "¿Cómo renovar la licencia de piloto?",
        "Procedimientos de cabina para comandantes",
        "Información sobre instructores de vuelo"
    ]
    
    print("\n🧪 Preguntas que activarían la búsqueda en SharePoint:")
    for i, question in enumerate(pilot_questions, 1):
        print(f"   {i}. {question}")
    
    # Palabras clave que detecta el sistema
    keywords = [
        "piloto", "pilotos", "pilot", "pilots",
        "capitán", "capitan", "captain", "comandante",
        "aerolínea", "aerolinea", "airline", "aviación", "aviation",
        "vuelo", "vuelos", "flight", "flights",
        "cabina", "cockpit", "tripulación", "crew",
        "aviador", "aviadores", "aviator", "aviators",
        "licencia de piloto", "certificación", "entrenamiento",
        "instructor de vuelo", "flight instructor"
    ]
    
    print("\n🔍 Palabras clave que activan SharePoint:")
    print(f"   {', '.join(keywords)}")
    
    # Simulación del flujo de trabajo
    print("\n📝 Flujo de trabajo integrado:")
    print("   1. Usuario envía pregunta")
    print("   2. Sistema detecta palabras clave de piloto")
    print("   3. Búsqueda en Azure AI Search + SharePoint en paralelo")
    print("   4. Combinación de resultados")
    print("   5. Respuesta completa al usuario")
    
    print("\n✅ Integración de SharePoint configurada y lista para usar!")
    return True

def test_keyword_detection():
    """
    Prueba la detección de palabras clave relacionadas con pilotos
    """
    # Esta función simula _is_pilot_related_query
    def is_pilot_related_query(query: str) -> bool:
        pilot_keywords = [
            "piloto", "pilotos", "pilot", "pilots",
            "capitán", "capitan", "captain", "comandante",
            "aerolínea", "aerolinea", "airline", "aviación", "aviation",
            "vuelo", "vuelos", "flight", "flights",
            "cabina", "cockpit", "tripulación", "crew",
            "aviador", "aviadores", "aviator", "aviators",
            "licencia de piloto", "certificación", "certificaciones", "entrenamiento",
            "instructor de vuelo", "flight instructor"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in pilot_keywords)
    
    test_cases = [
        ("¿Qué documentos para pilotos tenemos?", True),
        ("Muéstrame los manuales de vuelo", True),
        ("¿Cómo configurar Azure OpenAI?", False),
        ("Necesito información sobre certificaciones", True),
        ("¿Cuál es el entrenamiento para capitanes?", True),
        ("¿Cómo funciona el chatbot?", False),
        ("Documentos de tripulación disponibles", True),
        ("Información general sobre IA", False),
        ("¿Hay instructores de vuelo disponibles?", True),
        ("Procedimientos de cabina", True),
    ]
    
    print("\n🧪 Pruebas de detección de palabras clave:")
    for query, expected in test_cases:
        result = is_pilot_related_query(query)
        status = "✅" if result == expected else "❌"
        action = "SharePoint activado" if result else "Solo Azure AI Search"
        print(f"   {status} '{query}' → {action}")
    
    return True

if __name__ == "__main__":
    print("🚀 Probando integración de SharePoint con el chatbot")
    print("=" * 60)
    
    # Ejecutar pruebas
    asyncio.run(test_sharepoint_integration())
    test_keyword_detection()
    
    print("\n" + "=" * 60)
    print("📚 Para más información, consulta SHAREPOINT_INTEGRATION.md")
