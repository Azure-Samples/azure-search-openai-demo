# Config package for SharePoint integration
# Re-export original config constants for compatibility

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar constantes del archivo config.py original
from config import *
