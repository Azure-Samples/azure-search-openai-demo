 #!/bin/sh

echo "Checking if authentication should be setup..."

AZURE_USE_AUTHENTICATION=$(azd env get-value AZURE_USE_AUTHENTICATION)
if [ "$AZURE_USE_AUTHENTICATION" != "true" ]; then
  echo "AZURE_USE_AUTHENTICATION is not set, skipping authentication setup."
  exit 0
fi

echo "AZURE_USE_AUTHENTICATION is set, proceeding with authentication setup..."

. ./scripts/load_python_env.sh

./.venv/bin/python ./scripts/auth_init.py
