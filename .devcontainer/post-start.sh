#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/workspaces/azure-search-openai-demo"
SESSION_NAME="aso-services"
BACKEND_PORT=50505
FRONTEND_PORT=5173

cd "${PROJECT_ROOT}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required for background services. Please run .devcontainer/post-create.sh first."
  exit 1
fi

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
elif command -v azd >/dev/null 2>&1 && [ -x .venv/bin/python ]; then
  echo "Loading azd environment variables via scripts/load_azd_env.py"
  .venv/bin/python scripts/load_azd_env.py || echo "Warning: Unable to load azd env variables."
fi

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  echo "tmux session ${SESSION_NAME} already running."
  exit 0
fi

BACKEND_CMD="cd ${PROJECT_ROOT}/app/backend && source ${PROJECT_ROOT}/.venv/bin/activate && export QUART_APP=main:app QUART_ENV=development QUART_DEBUG=0 LOADING_MODE_FOR_AZD_ENV_VARS=override && python -m quart run --host 0.0.0.0 --port ${BACKEND_PORT} --reload"
FRONTEND_CMD="cd ${PROJECT_ROOT}/app/frontend && npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT}"

tmux new-session -d -s "${SESSION_NAME}" -n backend "bash -lc '${BACKEND_CMD}'"
tmux new-window -t "${SESSION_NAME}" -n frontend "bash -lc '${FRONTEND_CMD}'"

echo "Started backend on port ${BACKEND_PORT} and frontend on port ${FRONTEND_PORT} in tmux session ${SESSION_NAME}."
