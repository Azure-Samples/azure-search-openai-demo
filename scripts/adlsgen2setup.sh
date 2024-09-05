 #!/bin/sh

# Get the project root of the current script
project_root="$(cd "$(dirname $(dirname $0))" && pwd)"
script_dir="$project_root/scripts"
data_dir="$project_root/data"

. $script_dir/loadenv.sh

if [ -n "$AZURE_ADLS_GEN2_STORAGE_ACCOUNT" ]; then
    echo 'AZURE_ADLS_GEN2_STORAGE_ACCOUNT must be set to continue'
    exit 1
fi

echo 'Running "adlsgen2setup.py"'

./.venv/bin/python $script_dir/adlsgen2setup.py "$data_dir/*" --data-access-control "$script_dir/sampleacls.json" --storage-account "$AZURE_ADLS_GEN2_STORAGE_ACCOUNT" -v
