#!/bin/bash

# Azure OpenAI Model Deployment Setup
# Deploys required models: gpt-4o and text-embedding-3-large

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Azure OpenAI Model Deployment Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Load environment
if [ -f ".azure/prod/.env" ]; then
    export $(cat ".azure/prod/.env" | grep -E "^AZURE_" | xargs)
else
    echo -e "${RED}❌ Environment file not found. Run: azd provision${NC}"
    exit 1
fi

echo -e "${YELLOW}Deploying models to: ${BLUE}$AZURE_OPENAI_SERVICE${NC}"
echo ""

# Deploy gpt-4o model
echo -e "${YELLOW}[1/2] Deploying gpt-4o (Chat Model)...${NC}"

az cognitiveservices account deployment create \
  --resource-group $AZURE_OPENAI_RESOURCE_GROUP \
  --name $AZURE_OPENAI_SERVICE \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version 2024-05-13 \
  --sku Standard \
  --capacity 100 \
  --output none

echo -e "${GREEN}✅ gpt-4o deployed${NC}"

# Deploy text-embedding-3-large model
echo -e "${YELLOW}[2/2] Deploying text-embedding-3-large (Embeddings)...${NC}"

az cognitiveservices account deployment create \
  --resource-group $AZURE_OPENAI_RESOURCE_GROUP \
  --name $AZURE_OPENAI_SERVICE \
  --deployment-name text-embedding-3-large \
  --model-name text-embedding-3-large \
  --model-version 1 \
  --sku Standard \
  --capacity 350 \
  --output none

echo -e "${GREEN}✅ text-embedding-3-large deployed${NC}"

# Verify deployments
echo -e "\n${YELLOW}Verifying model deployments...${NC}"

DEPLOYMENTS=$(az cognitiveservices account deployment list \
  --resource-group $AZURE_OPENAI_RESOURCE_GROUP \
  --name $AZURE_OPENAI_SERVICE \
  --query "[].name" \
  -o tsv)

echo -e "${BLUE}Deployed models:${NC}"
for deployment in $DEPLOYMENTS; do
    echo "  • $deployment"
done

echo -e "\n${GREEN}✅ Model deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Update your environment variables:${NC}"
echo "  AZURE_OPENAI_DEPLOYMENT_CHATGPT=gpt-4o"
echo "  AZURE_OPENAI_CHATGPT_MODEL=gpt-4o"
echo "  AZURE_OPENAI_DEPLOYMENT_EMB=text-embedding-3-large"
echo "  AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-3-large"
echo "  AZURE_OPENAI_EMB_DIMENSIONS=1536"
