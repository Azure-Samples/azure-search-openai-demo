#!/bin/bash
# Save as check-services.sh

echo "=== Checking Azure Services Status ==="

# Get environment values
RG=$(azd env get-value AZURE_RESOURCE_GROUP)
echo "Resource Group: $RG"

# Check web apps
echo -e "\n=== Web Apps Status ==="
az webapp list -g $RG --query "[].{name:name, state:state, url:defaultHostName}" -o table

# Check search service
echo -e "\n=== Search Service ==="
SEARCH=$(azd env get-value AZURE_SEARCH_SERVICE)
az search service show -g $RG -n $SEARCH --query "{name:name, status:status, provisioningState:provisioningState}" -o table

# Check OpenAI
echo -e "\n=== OpenAI Service ==="
OPENAI=$(azd env get-value AZURE_OPENAI_SERVICE)
az cognitiveservices account show -g $RG -n $OPENAI --query "{name:name, provisioningState:properties.provisioningState, endpoint:properties.endpoint}" -o table

# Check storage
echo -e "\n=== Storage Account ==="
STORAGE=$(azd env get-value AZURE_STORAGE_ACCOUNT)
az storage account show -g $RG -n $STORAGE --query "{name:name, provisioningState:provisioningState, status:statusOfPrimary}" -o table

echo -e "\n=== Checking Complete ==="