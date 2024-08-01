#!/bin/bash

set -euo pipefail

# Retrieve values using Azure CLI
RESOURCE_GROUP=$(azd env get-value AZURE_RESOURCE_GROUP)

AZURE_SEARCH_INDEX=$(azd env get-value AZURE_SEARCH_INDEX)
AZURE_SEARCH_SERVICE=$(azd env get-value AZURE_SEARCH_SERVICE)

AZURE_OPENAI_SERVICE=$(azd env get-value AZURE_OPENAI_SERVICE)
AZURE_OPENAI_EVAL_DEPLOYMENT=$(azd env get-value AZURE_OPENAI_CHATGPT_DEPLOYMENT)
AZURE_OPENAI_EVAL_ENDPOINT=$(az cognitiveservices account show --name $AZURE_OPENAI_SERVICE --resource-group $RESOURCE_GROUP --query "properties.endpoint" -o tsv)

WEBAPP_NAME=$(az webapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
BACKEND_URI=$(az webapp show --resource-group $RESOURCE_GROUP --name $WEBAPP_NAME --query "defaultHostName" -o tsv)

# Populate the .env file
cat <<EOL > evaluation/.env
OPENAI_HOST="${OPENAI_HOST:-azure}"
OPENAI_GPT_MODEL="${OPENAI_GPT_MODEL:-gpt-35-turbo}"

# For generating QA based on AI Search index:
AZURE_SEARCH_SERVICE="$AZURE_SEARCH_SERVICE"
AZURE_SEARCH_INDEX="$AZURE_SEARCH_INDEX"
AZURE_SEARCH_KEY="${AZURE_SEARCH_KEY:-}"

# Evaluation Target URL
BACKEND_URI="https://$BACKEND_URI"

# For Azure authentication with keys:
AZURE_OPENAI_KEY="${AZURE_OPENAI_KEY:-}"

# For Azure OpenAI only:
AZURE_OPENAI_SERVICE="$AZURE_OPENAI_SERVICE"
AZURE_OPENAI_EVAL_DEPLOYMENT="$AZURE_OPENAI_EVAL_DEPLOYMENT"
AZURE_OPENAI_EVAL_ENDPOINT="$AZURE_OPENAI_EVAL_ENDPOINT"

# For openai.com only:
OPENAICOM_KEY="${OPENAICOM_KEY:-}"
OPENAICOM_ORGANIZATION="${OPENAICOM_ORGANIZATION:-}"

# For PyRIT:
# Azure ML Target (only needed when the model under evaluation is hosted on Azure ML)
AZURE_ML_ENDPOINT="${AZURE_ML_ENDPOINT:-}"
AZURE_ML_MANAGED_KEY="${AZURE_ML_MANAGED_KEY:-}"
EOL

echo "evaluation/.env file has been populated successfully"
