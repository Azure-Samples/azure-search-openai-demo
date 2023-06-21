 #!/bin/sh

echo ""
echo "Loading azd .env file from current environment"
echo ""

current_dir=$(pwd)

while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    export "$key=$value"
done <<EOF
$(azd env get-values)
EOF

echo 'Creating python virtual environment "scripts/.venv"'

if command -v python3 &>/dev/null; then
    python3 -m venv $current_dir/scripts/.venv
else
    python -m venv $current_dir/scripts/.venv
fi


echo 'Installing dependencies from "requirements.txt" into virtual environment'
./scripts/.venv/bin/python -m pip install -r $current_dir/requirements.txt

echo 'Running "prepdocs.py"'
./scripts/.venv/bin/python $current_dir/prepdocs.py './data/*' --storageaccount "$AZURE_STORAGE_ACCOUNT" --container "$AZURE_STORAGE_CONTAINER" --searchservice "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" --formrecognizerservice "$AZURE_FORMRECOGNIZER_SERVICE" --tenantid "$AZURE_TENANT_ID" -v
