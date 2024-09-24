 #!/bin/sh

. ./scripts/load_python_env.sh

echo 'Running "prepdocs.py"'

AZURE_USE_AUTHENTICATION=$(azd env get-value AZURE_PUBLIC_NETWORK_ACCESS)
AZURE_PUBLIC_NETWORK_ACCESS=$(azd env get-value AZURE_PUBLIC_NETWORK_ACCESS)

if [ -n "$AZURE_USE_AUTHENTICATION" ] && [ "$AZURE_PUBLIC_NETWORK_ACCESS" = "Disabled" ]; then
  echo "AZURE_PUBLIC_NETWORK_ACCESS is set to Disabled. Exiting."
  exit 0
fi

additionalArgs=""
if [ $# -gt 0 ]; then
  additionalArgs="$@"
fi

./.venv/bin/python ./app/backend/prepdocs.py './data/*' --verbose $additionalArgs
