#!/usr/bin/env python3
"""
Script de validación para los cambios del Frontend de Pilotos
"""

import json
import os

def validate_translation_file(file_path, language_name):
    """Valida que un archivo de traducción tenga el contenido correcto para pilotos"""
    
    print(f"\n📋 Validando traducciones en {language_name} ({file_path})...")
    
    if not os.path.exists(file_path):
        print(f"❌ Archivo no encontrado: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        # Validar títulos
        required_fields = [
            'pageTitle', 'headerTitle', 'chatEmptyStateTitle', 
            'chatEmptyStateSubtitle', 'defaultExamples', 'gpt4vExamples'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in translations:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Campos faltantes: {missing_fields}")
            return False
        
        # Validar que los títulos contengan referencias a pilotos
        pilot_keywords = ['pilot', 'piloto', 'aviation', 'aviación', 'airline', 'aerolínea']
        
        title_fields = ['pageTitle', 'headerTitle', 'chatEmptyStateTitle']
        for field in title_fields:
            title = translations[field].lower()
            if not any(keyword in title for keyword in pilot_keywords):
                print(f"⚠️  Campo '{field}' podría no estar actualizado para pilotos: {translations[field]}")
        
        # Validar ejemplos
        default_examples = translations['defaultExamples']
        if not isinstance(default_examples, dict):
            print(f"❌ defaultExamples debe ser un objeto")
            return False
        
        # Verificar que hay al menos 3 ejemplos
        example_keys = ['1', '2', '3']
        for key in example_keys:
            if key not in default_examples:
                print(f"❌ Falta ejemplo {key}")
                return False
        
        print(f"✅ {language_name}: Traducciones válidas")
        print(f"   📝 Título: {translations['chatEmptyStateTitle']}")
        print(f"   📋 Ejemplos: {len([k for k in default_examples.keys() if k.isdigit()])} encontrados")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Error de JSON en {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def validate_html_title():
    """Valida que el título HTML esté actualizado"""
    
    print(f"\n📋 Validando título HTML...")
    
    html_path = "/workspaces/azure-search-openai-demo/app/frontend/index.html"
    
    if not os.path.exists(html_path):
        print(f"❌ Archivo no encontrado: {html_path}")
        return False
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "Asistente AI para Pilotos" in content or "AI Assistant for Pilots" in content:
            print("✅ HTML: Título actualizado correctamente")
            return True
        else:
            print("❌ HTML: Título no parece estar actualizado para pilotos")
            return False
            
    except Exception as e:
        print(f"❌ Error leyendo HTML: {e}")
        return False

def main():
    print("🚀 Validando actualizaciones del Frontend para Pilotos")
    print("=" * 60)
    
    base_path = "/workspaces/azure-search-openai-demo/app/frontend/src/locales"
    
    # Archivos de traducción a validar
    translation_files = [
        (f"{base_path}/es/translation.json", "Español"),
        (f"{base_path}/en/translation.json", "Inglés"),
        (f"{base_path}/fr/translation.json", "Francés"),
    ]
    
    results = []
    
    # Validar archivos de traducción
    for file_path, language in translation_files:
        success = validate_translation_file(file_path, language)
        results.append((language, success))
    
    # Validar HTML
    html_success = validate_html_title()
    results.append(("HTML", html_success))
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {name}")
    
    print(f"\n🎯 Resultado: {passed_tests}/{total_tests} pruebas pasaron")
    
    if passed_tests == total_tests:
        print("🎉 ¡Todas las validaciones pasaron! El frontend está listo para pilotos.")
    else:
        print("⚠️  Algunas validaciones fallaron. Revisar los errores arriba.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
