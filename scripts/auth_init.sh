 #!/bin/sh

echo "Checking if authentication should be setup..."

. ./scripts/load_azd_env.sh

if [ -z "$AZURE_USE_AUTHENTICATION" ]; then
  echo "AZURE_USE_AUTHENTICATION is not set, skipping authentication setup."
  exit 0
fi

echo "AZURE_USE_AUTHENTICATION is set, proceeding with authentication setup..."

. ./scripts/load_python_env.sh

./.venv/bin/python ./scripts/auth_init.py
