#!/bin/bash

output=$(azd env get-values)

while IFS= read -r line; do
    name=$(echo "$line" | cut -d'=' -f1)
    value=$(echo "$line" | cut -d'=' -f2- | sed 's/^"\|"$//g')
    export "$name"="$value"
done <<< "$output"

echo "Environment variables set."

pip install -r ./scripts/requirements.txt

python ./scripts/prepdocs.py './data/*' --storageaccount "$AZURE_STORAGE_ACCOUNT" --container "$AZURE_STORAGE_CONTAINER" --searchservice "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" -v