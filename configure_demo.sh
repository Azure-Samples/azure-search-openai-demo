#!/usr/bin/env bash
# configure_demo.sh – prepares azd environment for the public demo using existing resource group & storage account
set -euo pipefail

# ----- parameters you may tweak -----
RG="rg-jacob-paul-rag"                        # existing resource group
SUB="6c8e23df-4aec-4ed5-bec5-79853ea6c6c6"   # subscription id
LOC="eastus2"                                # default location
ENV_NAME="demo"                              # azd env folder name
STORAGE_ACCT="stinternalrag001"              # existing ADLS Gen2 account

# fixed resource names following pattern <abbr>-internal-3c-rag
SEARCH="srch-internal-3c-rag"
OPENAI="oai-internal-3c-rag"
DOCINT="di-internal-3c-rag"
SPEECH="spch-internal-3c-rag"
PLAN="asp-internal-3c-rag"
WEBAPP="app-internal-3c-rag"
COSMOS="cosmosinternal3crag"    # Cosmos account names cannot have hyphens

# ----- create / switch azd env -----
# create or switch to environment
if azd env list --output json | grep -q "\"$ENV_NAME\""; then
  echo "Selecting existing environment $ENV_NAME"
  azd env select "$ENV_NAME"
else
  azd env new "$ENV_NAME" --subscription "$SUB" --location "$LOC"
fi
# pin to existing resource group
azd env set AZURE_RESOURCE_GROUP "$RG"

# ----- hosting SKUs / flags -----
azd env set DEPLOYMENT_TARGET appservice
azd env set AZURE_APP_SERVICE_SKU P0v3
azd env set AZURE_SEARCH_SERVICE_SKU standard
azd env set SERVICE_WEB_RESOURCE_EXISTS true

# ----- explicit resource names -----
azd env set AZURE_STORAGE_ACCOUNT           "$STORAGE_ACCT"
azd env set AZURE_STORAGE_CONTAINER        "content"
azd env set AZURE_STORAGE_RESOURCE_GROUP   "$RG"
azd env set AZURE_APPLICATION_INSIGHTS     "appi-internal-3c-rag"
azd env set AZURE_APPLICATION_INSIGHTS_DASHBOARD "dash-internal-3c-rag"
azd env set AZURE_LOG_ANALYTICS            "log-internal-3c-rag"
azd env set AZURE_SEARCH_SERVICE            "$SEARCH"
azd env set AZURE_OPENAI_SERVICE            "$OPENAI"
azd env set AZURE_DOCUMENTINTELLIGENCE_SERVICE "$DOCINT"
azd env set AZURE_SPEECH_SERVICE            "$SPEECH"
azd env set AZURE_APP_SERVICE_PLAN          "$PLAN"
azd env set AZURE_APP_SERVICE               "$WEBAPP"
azd env set AZURE_COSMOSDB_ACCOUNT          "$COSMOS"

# ----- model / vision -----
azd env set AZURE_OPENAI_EMB_MODEL_NAME  text-embedding-3-large
azd env set AZURE_OPENAI_EMB_DIMENSIONS  3072
# Enable GPT-4 Vision feature flag expected by template
azd env set USE_GPT4V true
# Optional: set the GPT-4V deployment/model names (can be blank to let template default)
azd env set AZURE_OPENAI_GPT4V_MODEL gpt-4o
azd env set AZURE_OPENAI_GPT4V_DEPLOYMENT gpt4v
azd env set USE_MEDIA_DESCRIBER_AZURE_CU false

# ----- retrieval options -----
azd env set AZURE_SEARCH_SEMANTIC_RANKER standard
azd env set AZURE_SEARCH_QUERY_REWRITING true

# ----- chat history -----
azd env set USE_CHAT_HISTORY_COSMOS true

# ----- speech -----
azd env set USE_SPEECH_INPUT_BROWSER  true
azd env set USE_SPEECH_OUTPUT_AZURE  true
azd env set AZURE_SPEECH_SERVICE_VOICE en-US-AndrewMultilingualNeural

# ----- security & uploads -----
azd env set AZURE_USE_AUTHENTICATION true
TENANT_ID=$(az account show --query tenantId -o tsv 2>/dev/null || echo "")
if [ -n "$TENANT_ID" ]; then
  azd env set AZURE_AUTH_TENANT_ID "$TENANT_ID"
  azd env set AZURE_TENANT_ID "$TENANT_ID"
fi
azd env set USE_USER_UPLOAD true

# content understanding (Azure AI Foundry account)
azd env set AZURE_COMPUTER_VISION_SERVICE  "cu-internal-3c-rag"

# user-upload storage account (ADLS Gen2)
azd env set AZURE_ADLS_GEN2_STORAGE_ACCOUNT "userstinternal3crag"
azd env set AZURE_ADLS_GEN2_FILESYSTEM      "user-content"
azd env set AZURE_ADLS_GEN2_FILESYSTEM_PATH ""

# ----- regional parameters to avoid interactive prompts -----
# keep required uppercase vars
azd env set AZURE_OPENAI_LOCATION "$LOC"
azd env set AZURE_DOCUMENTINTELLIGENCE_LOCATION "eastus"

echo "✔ Demo environment configured. Run 'azd up' next." 