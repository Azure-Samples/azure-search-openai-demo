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

echo "Running manageacl.py. Arguments to script: $@"
  ./scripts/.venv/bin/python ./scripts/manageacl.py --search-service "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" $@
  