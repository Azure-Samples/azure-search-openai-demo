#!/bin/sh

AZURE_USE_PRIVATE_ENDPOINT=$(azd env get-value AZURE_USE_PRIVATE_ENDPOINT 2>/dev/null)
if [ "$AZURE_USE_PRIVATE_ENDPOINT" != "true" ]; then
  exit 0
fi

. ./scripts/load_python_env.sh

./.venv/bin/python ./scripts/approve_search_private_links.py
