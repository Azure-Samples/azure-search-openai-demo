#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/workspaces/azure-search-openai-demo"
cd "${PROJECT_ROOT}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "Installing tmux to manage background services..."
  sudo apt-get update -y
  sudo apt-get install -y tmux
fi

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r app/backend/requirements.txt

pushd app/frontend >/dev/null
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi
popd >/dev/null

# If a local .env doesn't exist but a template does, copy it so the start script has values to source.
if [ ! -f .env ] && [ -f .env.template ]; then
  echo "Creating local .env from .env.template (contains safe placeholders)."
  cp .env.template .env
  echo "NOTE: .env contains placeholder values. Replace them with your real values for local development."
fi

echo "Dependency bootstrap complete."
