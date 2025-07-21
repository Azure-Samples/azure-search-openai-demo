import os

from dotenv import load_dotenv
from app import create_app
from load_azd_env import load_azd_env

# Cargar variables de entorno desde archivo .env local si existe
load_dotenv()

# WEBSITE_HOSTNAME is always set by App Service, RUNNING_IN_PRODUCTION is set in main.bicep
RUNNING_ON_AZURE = os.getenv("WEBSITE_HOSTNAME") is not None or os.getenv("RUNNING_IN_PRODUCTION") is not None

if not RUNNING_ON_AZURE:
    load_azd_env()

app = create_app()
