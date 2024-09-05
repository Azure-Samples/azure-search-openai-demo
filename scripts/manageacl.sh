 #!/bin/sh

# Get the project root of the current script
project_root="$(cd "$(dirname $(dirname $0))" && pwd)"
script_dir="$project_root/scripts"

. $script_dir/loadenv.sh

echo "Running manageacl.py. Arguments to script: $@"
  ./.venv/bin/python $script_dir/manageacl.py --search-service "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" $@
