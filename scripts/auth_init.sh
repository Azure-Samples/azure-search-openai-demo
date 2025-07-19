#!/bin/sh

echo "Checking if authentication should be setup..."

AZURE_USE_AUTHENTICATION=$(azd env get-value AZURE_USE_AUTHENTICATION)
AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS=$(azd env get-value AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS)
AZURE_ENFORCE_ACCESS_CONTROL=$(azd env get-value AZURE_ENFORCE_ACCESS_CONTROL)
USE_CHAT_HISTORY_COSMOS=$(azd env get-value USE_CHAT_HISTORY_COSMOS)

if [ "$AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS" = "true" ]; then
  if [ "$AZURE_ENFORCE_ACCESS_CONTROL" != "true" ]; then
    echo "AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS is set to true, but AZURE_ENFORCE_ACCESS_CONTROL is not set to true. Please set and retry."
    exit 1
  fi
fi

if [ "$USE_CHAT_HISTORY_COSMOS" = "true" ]; then
  if [ "$AZURE_USE_AUTHENTICATION" != "true" ]; then
    echo "USE_CHAT_HISTORY_COSMOS is set to true, but AZURE_USE_AUTHENTICATION is not set to true. Please set and retry."
    exit 1
  fi
fi

if [ "$AZURE_USE_AUTHENTICATION" != "true" ]; then
  echo "AZURE_USE_AUTHENTICATION is not set, skipping authentication setup."
  exit 0
fi

echo "AZURE_USE_AUTHENTICATION is set, proceeding with authentication setup..."

. ./scripts/load_python_env.sh

./.venv/bin/python ./scripts/auth_init.py
