 #!/bin/sh

# Get the project root of the current script
project_root="$(cd "$(dirname $(dirname $0))" && pwd)"
script_dir="$project_root/scripts"
data_dir="$project_root/data"

echo "Checking if authentication should be setup..."

. $script_dir/load_azd_env.sh

if [ -z "$AZURE_USE_AUTHENTICATION" ]; then
  echo "AZURE_USE_AUTHENTICATION is not set, skipping authentication setup."
  exit 0
fi

echo "AZURE_USE_AUTHENTICATION is set, proceeding with authentication setup..."

. $script_dir/load_python_env.sh

./.venv/bin/python $script_dir/auth_init.py
