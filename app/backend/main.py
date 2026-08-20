import os

from dotenv_azd import load_azd_env

from app import create_app

# WEBSITE_HOSTNAME is always set by App Service, RUNNING_IN_PRODUCTION is set in main.bicep
RUNNING_ON_AZURE = os.getenv("WEBSITE_HOSTNAME") is not None or os.getenv("RUNNING_IN_PRODUCTION") is not None

if not RUNNING_ON_AZURE:
    load_azd_env(override=os.getenv("LOADING_MODE_FOR_AZD_ENV_VARS") != "no-override")

app = create_app()
