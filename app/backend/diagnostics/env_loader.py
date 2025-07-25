"""
Cargador central de variables de entorno para diagnósticos
"""

import os

def load_env_file():
    """Carga las variables de entorno del archivo .azure/dev/.env"""
    try:
        # Buscar el archivo .env en .azure/dev/
        env_file = None
        current_dir = os.getcwd()
        
        # Buscar desde el directorio actual hacia arriba
        while current_dir != "/":
            potential_env = os.path.join(current_dir, ".azure", "dev", ".env")
            if os.path.exists(potential_env):
                env_file = potential_env
                break
            current_dir = os.path.dirname(current_dir)
        
        if not env_file:
            print("⚠️ No se encontró archivo .azure/dev/.env")
            return False
        
        # Cargar variables del archivo
        loaded_count = 0
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remover comillas si existen
                    value = value.strip('"\'')
                    os.environ[key] = value
                    loaded_count += 1
        
        print(f"🔍 Variables cargadas desde: {env_file} ({loaded_count} variables)")
        return True
        
    except Exception as e:
        print(f"⚠️ Error cargando variables de entorno: {e}")
        return False

# Cargar variables automáticamente al importar
load_env_file()
