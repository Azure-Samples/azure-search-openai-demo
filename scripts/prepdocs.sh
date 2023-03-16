 #!/bin/sh

echo ""
echo "Loading azd .env file from current environment"
echo ""

# Run the command and capture the output
output=$(azd env get-values)

# Loop over each line of the output and extract the key and value
echo "$output" | while read line; do
  # Split the line into key and value
  key=$(echo "$line" | cut -d= -f1)
  value=$(echo "$line" | cut -d= -f2-)

  # Remove the double quotes from the value using sed
  value=$(echo "$value" | sed 's/"//g')

  # Set the environment variable
  export "$key"="$value"
done


echo 'Creating python virtual environment "scripts/.venv"'
python -m venv scripts/.venv

echo 'Installing dependencies from "requirements.txt" into virtual environment'
./scripts/.venv/bin/python -m pip install -r scripts/requirements.txt

echo 'Running "prepdocs.py"'
./scripts/.venv/bin/python ./scripts/prepdocs.py './data/*' --storageaccount "$AZURE_STORAGE_ACCOUNT" --container "$AZURE_STORAGE_CONTAINER" --searchservice "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" -v