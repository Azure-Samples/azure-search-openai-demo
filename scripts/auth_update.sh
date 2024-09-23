 #!/bin/sh

AZURE_USE_AUTHENTICATION=$(azd env get-value AZURE_USE_AUTHENTICATION)
if [ $? -ne 0 ]; then
  exit 0
fi

. ./scripts/load_python_env.sh

./.venv/bin/python ./scripts/auth_update.py
