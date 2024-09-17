 #!/bin/sh

echo "Checking if authentication should be setup..."

. ./scripts/load_azd_env.sh

if [ "$AZURE_USE_AUTHENTICATION" = "true" ]; then
    echo "AZURE_USE_AUTHENTICATION is true, proceeding with authentication setup..."
    . ./scripts/load_python_env.sh
    ./.venv/bin/python ./scripts/auth_init.py
else
    echo "AZURE_USE_AUTHENTICATION is not true, skipping authentication setup."
    exit 0
fi