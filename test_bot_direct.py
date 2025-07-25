#!/usr/bin/env python3
"""
Script de diagnóstico directo para probar el bot y ver errores detallados
"""
import os
import sys
import asyncio
import json
import traceback

# Agregar el directorio actual al path
sys.path.insert(0, '/workspaces/azure-search-openai-demo/app/backend')

async def test_bot_direct():
    """Prueba directa del bot sin servidor web"""
    try:
        print("🔍 Cargando configuración...")
        
        # Cargar variables de entorno
        from dotenv import load_dotenv
        env_path = '/workspaces/azure-search-openai-demo/.azure/dev/.env'
        load_dotenv(env_path)
        print(f"✅ Variables cargadas desde: {env_path}")
        
        # Importar módulos necesarios
        print("🔍 Importando módulos...")
        from app import create_app
        
        print("🔍 Creando aplicación...")
        app = create_app()
        
        # Simular contexto de aplicación usando Quart
        async with app.app_context():
            print("🔍 Ejecutando setup_clients()...")
            from app import setup_clients
            await setup_clients()
            print("✅ Setup completado")
            
            print("🔍 Obteniendo approach...")
            from app import CONFIG_CHAT_APPROACH
            approach = app.config[CONFIG_CHAT_APPROACH]
            print(f"✅ Approach obtenido: {type(approach).__name__}")
            
            print("🔍 Preparando mensaje de prueba...")
            messages = [{"role": "user", "content": "Hola, ¿puedes ayudarme?"}]
            context = {"overrides": {}}
            session_state = "test-session"
            
            print("🚀 Ejecutando approach.run()...")
            result = await approach.run(
                messages=messages,
                context=context, 
                session_state=session_state
            )
            
            print("✅ ¡Éxito!")
            print(f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
    except Exception as e:
        print(f"❌ ERROR DETALLADO:")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        print(f"Traceback completo:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot_direct())
