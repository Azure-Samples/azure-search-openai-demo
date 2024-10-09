# Get the directory of the current script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Load environment variables from azd env
$subscriptionId = azd env get-value AZURE_SUBSCRIPTION_ID
$resourceName = azd env get-value AZURE_OPENAI_SERVICE
$resourceGroup = azd env get-value AZURE_OPENAI_RESOURCE_GROUP

# Run the Python script with the retrieved values
python "$scriptDir/pre-down.py" --subscription-id $subscriptionId --resource-name $resourceName --resource-group $resourceGroup
