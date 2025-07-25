"""
Utilidades de logging con colores para el sistema de diagnósticos
"""

try:
    from colorama import Fore, Style, init
    init()  # Inicializar colorama
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

def log_ok(msg):
    """Log de éxito con color verde"""
    if COLORAMA_AVAILABLE:
        print(Fore.GREEN + "✅ " + msg + Style.RESET_ALL)
    else:
        print("✅ " + msg)

def log_warn(msg):
    """Log de advertencia con color amarillo"""
    if COLORAMA_AVAILABLE:
        print(Fore.YELLOW + "⚠️ " + msg + Style.RESET_ALL)
    else:
        print("⚠️ " + msg)

def log_error(msg):
    """Log de error con color rojo"""
    if COLORAMA_AVAILABLE:
        print(Fore.RED + "❌ " + msg + Style.RESET_ALL)
    else:
        print("❌ " + msg)

def log_info(msg):
    """Log de información con color azul"""
    if COLORAMA_AVAILABLE:
        print(Fore.BLUE + "🔍 " + msg + Style.RESET_ALL)
    else:
        print("🔍 " + msg)

def log_debug(msg):
    """Log de debug con color magenta"""
    if COLORAMA_AVAILABLE:
        print(Fore.MAGENTA + "🐛 " + msg + Style.RESET_ALL)
    else:
        print("🐛 " + msg)
