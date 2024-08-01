# Set strict mode
Set-StrictMode -Version Latest

# Retrieve values using Azure CLI
$RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP

$AZURE_SEARCH_INDEX = azd env get-value AZURE_SEARCH_INDEX
$AZURE_SEARCH_SERVICE = azd env get-value AZURE_SEARCH_SERVICE

$AZURE_OPENAI_SERVICE = azd env get-value AZURE_OPENAI_SERVICE
$AZURE_OPENAI_EVAL_DEPLOYMENT = azd env get-value AZURE_OPENAI_CHATGPT_DEPLOYMENT
$AZURE_OPENAI_EVAL_ENDPOINT = az cognitiveservices account show --name $AZURE_OPENAI_SERVICE --resource-group $RESOURCE_GROUP --query "properties.endpoint" -o tsv

$WEBAPP_NAME = az webapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv
$BACKEND_URI = az webapp show --resource-group $RESOURCE_GROUP --name $WEBAPP_NAME --query "defaultHostName" -o tsv

# Populate the .env file
$envContent = @"
OPENAI_HOST="${env:OPENAI_HOST -replace '^\s*$', 'azure'}"
OPENAI_GPT_MODEL="${env:OPENAI_GPT_MODEL -replace '^\s*$', 'gpt-35-turbo'}"

# For generating QA based on AI Search index:
AZURE_SEARCH_SERVICE="$AZURE_SEARCH_SERVICE"
AZURE_SEARCH_INDEX="$AZURE_SEARCH_INDEX"
AZURE_SEARCH_KEY="${env:AZURE_SEARCH_KEY -replace '^\s*$', ''}"

# Evaluation Target URL
BACKEND_URI="https://$BACKEND_URI"

# For Azure authentication with keys:
AZURE_OPENAI_KEY="${env:AZURE_OPENAI_KEY -replace '^\s*$', ''}"

# For Azure OpenAI only:
AZURE_OPENAI_SERVICE="$AZURE_OPENAI_SERVICE"
AZURE_OPENAI_EVAL_DEPLOYMENT="$AZURE_OPENAI_EVAL_DEPLOYMENT"
AZURE_OPENAI_EVAL_ENDPOINT="$AZURE_OPENAI_EVAL_ENDPOINT"

# For openai.com only:
OPENAICOM_KEY="${env:OPENAICOM_KEY -replace '^\s*$', ''}"
OPENAICOM_ORGANIZATION="${env:OPENAICOM_ORGANIZATION -replace '^\s*$', ''}"

# For PyRIT:
# Azure ML Target (only needed when the model under evaluation is hosted on Azure ML)
AZURE_ML_ENDPOINT="${env:AZURE_ML_ENDPOINT -replace '^\s*$', ''}"
AZURE_ML_MANAGED_KEY="${env:AZURE_ML_MANAGED_KEY -replace '^\s*$', ''}"
"@

Set-Content -Path "evaluation/.env" -Value $envContent

Write-Output "evaluation/.env file has been populated successfully"
