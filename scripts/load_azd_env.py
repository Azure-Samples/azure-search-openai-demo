import json
import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("scripts")


def _load_env_file(env_path: Path, override: bool) -> bool:
    if env_path.is_file():
        logger.info("Loading environment variables from %s", env_path)
        load_dotenv(env_path, override=override)
        return True
    return False


def load_azd_env():
    """Get path to current azd env file and load file using python-dotenv"""
    loading_mode = os.getenv("LOADING_MODE_FOR_AZD_ENV_VARS") or "override"
    override = loading_mode != "no-override"

    result = subprocess.run("azd env list -o json", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        env_json = json.loads(result.stdout)
        env_file_path = None
        for entry in env_json:
            if entry.get("IsDefault"):
                env_file_path = entry.get("DotEnvPath")
                break
        if env_file_path and Path(env_file_path).is_file():
            logger.info("Loading azd env from %s", env_file_path)
            load_dotenv(env_file_path, override=override)
            return
        logger.warning("No default azd env file reported by azd. Falling back to local .env if present.")
    else:
        logger.warning("azd env list failed (%s). Falling back to local .env if present.", result.returncode)

    repo_root = Path(__file__).resolve().parents[1]
    local_env = repo_root / ".env"
    if _load_env_file(local_env, override):
        return

    logger.warning("No azd environment or local .env file found. Continuing without loading additional env vars.")
