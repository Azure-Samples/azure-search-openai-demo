 #!/bin/sh

echo ""
echo "Loading azd .env file from current environment"
echo ""

while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    export "$key=$value"
done <<EOF
$(azd env get-values)
EOF

echo 'Creating python virtual environment "scripts/.venv"'
python3 -m venv scripts/.venv

echo 'Installing dependencies from "requirements.txt" into virtual environment'
./scripts/.venv/bin/python -m pip install -r scripts/requirements.txt

if [ -n "$AZURE_ADLS_GEN2_STORAGE_ACCOUNT" ]; then
    echo 'AZURE_ADLS_GEN2_STORAGE_ACCOUNT must be set to continue'
    exit 1
fi

echo 'Running "adlsgen2setup.py"'

./scripts/.venv/bin/python ./scripts/adlsgen2setup.py './data/*' --storage-account "$AZURE_ADLS_GEN2_STORAGE_ACCOUNT" -v
