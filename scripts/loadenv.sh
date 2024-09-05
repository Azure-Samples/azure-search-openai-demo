 #!/bin/sh

# Get the project root of the current script
project_root="$(cd "$(dirname $(dirname $0))" && pwd)"
script_dir="$project_root/scripts"

. $script_dir/load_azd_env.sh

. $script_dir/load_python_env.sh
