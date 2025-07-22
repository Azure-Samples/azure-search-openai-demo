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
        raise Exception("Error loading azd env")
    env_json = json.loads(result.stdout)
    env_file_path = None
    for entry in env_json:
        if entry["IsDefault"]:
            env_file_path = entry["DotEnvPath"]
    if not env_file_path:
        raise Exception("No default azd env file found")
    loading_mode = os.getenv("LOADING_MODE_FOR_AZD_ENV_VARS") or "override"
    if loading_mode == "no-override":
        logger.info("Loading azd env from %s, but not overriding existing environment variables", env_file_path)
        load_dotenv(env_file_path, override=False)
    else:
        logger.info("Loading azd env from %s, which may override existing environment variables", env_file_path)
        load_dotenv(env_file_path, override=True)
