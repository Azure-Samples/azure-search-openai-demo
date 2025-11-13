import json
import logging
import os
import subprocess

from dotenv import load_dotenv

logger = logging.getLogger("scripts")


def load_azd_env():
    """Get path to current azd env file and load file using python-dotenv"""
    result = subprocess.run("azd env list -o json", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback to loading .env file if azd is not available
        logger.info("azd not available, attempting to load .env file instead")
        env_file_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file_path):
            logger.info("Loading .env from %s", env_file_path)
            load_dotenv(env_file_path, override=True)
            return
        else:
            logger.warning("No .env file found at %s", env_file_path)
            return
    env_json = json.loads(result.stdout)
    env_file_path = None
    for entry in env_json:
        if entry["IsDefault"]:
            env_file_path = entry["DotEnvPath"]
    if not env_file_path:
        # Fallback to .env file
        logger.info("No default azd env found, attempting to load .env file instead")
        env_file_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file_path):
            logger.info("Loading .env from %s", env_file_path)
            load_dotenv(env_file_path, override=True)
            return
        else:
            logger.warning("No .env file found at %s", env_file_path)
            return
    loading_mode = os.getenv("LOADING_MODE_FOR_AZD_ENV_VARS") or "override"
    if loading_mode == "no-override":
        logger.info("Loading azd env from %s, but not overriding existing environment variables", env_file_path)
        load_dotenv(env_file_path, override=False)
    else:
        logger.info("Loading azd env from %s, which may override existing environment variables", env_file_path)
        load_dotenv(env_file_path, override=True)
    
    # Also load from local .env file as fallback (for variables not in azd env)
    local_env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(local_env_path) and local_env_path != env_file_path:
        logger.info("Also loading local .env from %s (as fallback for missing variables)", local_env_path)
        load_dotenv(local_env_path, override=False)  # Don't override azd vars, but fill in missing ones
