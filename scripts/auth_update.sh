 #!/bin/sh

. ./scripts/load_azd_env.sh

if [ -z "$AZURE_USE_AUTHENTICATION" ]; then
  exit 0
fi

. ./scripts/load_python_env.sh

./.venv/bin/python ./scripts/auth_update.py
