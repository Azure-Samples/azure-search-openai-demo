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

# Install Microsoft Edge for browser automation
echo "Installing Microsoft Edge..."
if ! command -v microsoft-edge >/dev/null 2>&1; then
  # Add Microsoft Edge repository
  curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-edge.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-edge.gpg] https://packages.microsoft.com/repos/edge stable main" | sudo tee /etc/apt/sources.list.d/microsoft-edge.list
  sudo apt-get update
  sudo apt-get install -y microsoft-edge-stable
  echo "✅ Microsoft Edge installed successfully"
else
  echo "✅ Microsoft Edge already installed"
fi

# Install Playwright browsers for automation
echo "Installing Playwright browsers..."
python -m playwright install chromium
python -m playwright install msedge || echo "⚠️  Edge browser driver not available, using Chromium"
python -m playwright install-deps
echo "✅ Playwright browsers installed"

# If a local .env doesn't exist but a template does, copy it so the start script has values to source.
if [ ! -f .env ] && [ -f .env.template ]; then
  echo "Creating local .env from .env.template (contains safe placeholders)."
  cp .env.template .env
  echo "NOTE: .env contains placeholder values. Replace them with your real values for local development."
fi

echo "Dependency bootstrap complete."
