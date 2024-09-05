 #!/bin/sh

# Get the project root of the current script
project_root="$(cd "$(dirname $(dirname $0))" && pwd)"
script_dir="$project_root/scripts"

. $script_dir/load_azd_env.sh

if [ -z "$AZURE_USE_AUTHENTICATION" ]; then
  exit 0
fi

. $script_dir/load_python_env.sh

./.venv/bin/python $script_dir/auth_update.py
