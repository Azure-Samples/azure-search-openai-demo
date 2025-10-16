#!/usr/bin/env bash
set -euo pipefail

# Lightweight runner for the MCP backend (Quart)
# Usage: ./run_mcp.sh [port]

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PORT=${1:-50505}

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip

if [ -f "$ROOT_DIR/app/backend/requirements.txt" ]; then
  pip install -r "$ROOT_DIR/app/backend/requirements.txt"
fi

cd "$ROOT_DIR/app/backend"
echo "Starting Quart backend on 0.0.0.0:$PORT"
exec "$VENV_DIR/bin/python" -m quart --app main:app run --host 0.0.0.0 --port "$PORT" --reload
