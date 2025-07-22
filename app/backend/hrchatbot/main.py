import asyncio
import os
import socket

from hrchatbot.app import create_app
from hrchatbot.load_azd_env import load_azd_env


def force_bind_port(desired_port=8000):
    """Force bind to port using SO_REUSEADDR"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("localhost", desired_port))
            return desired_port
        except OSError:
            # Still couldn't bind, find free port
            s.bind(("localhost", 0))
            return s.getsockname()[1]


RUNNING_ON_AZURE = (
    os.getenv("WEBSITE_HOSTNAME") is not None
    or os.getenv("RUNNING_IN_PRODUCTION") is not None
)

if not RUNNING_ON_AZURE:
    load_azd_env()

app = create_app()

if __name__ == "__main__":
    port = force_bind_port(8000)
    url = f"http://localhost:{port}"
    asyncio.run(app.run_task(host="localhost", port=port))
