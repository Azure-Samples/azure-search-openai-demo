#!/bin/bash

# Complete Foundry + Azure OpenAI Setup Script
# This script configures all necessary Azure services and Foundry integration
# Run: bash scripts/setup-foundry-azure.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Foundry + Azure OpenAI Complete Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Check prerequisites
echo -e "\n${YELLOW}[1/5] Checking prerequisites...${NC}"

if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI not found. Install from: https://docs.microsoft.com/cli/azure/install-azure-cli${NC}"
    exit 1
fi

if ! command -v azd &> /dev/null; then
    echo -e "${RED}❌ Azure Developer CLI not found. Install from: https://aka.ms/azd${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites met${NC}"

# Initialize Azure Developer CLI
echo -e "\n${YELLOW}[2/5] Initializing Azure Developer CLI...${NC}"

if [ ! -f ".azd-initialized" ]; then
    azd init -t ./
    touch .azd-initialized
    echo -e "${GREEN}✅ Azure Developer CLI initialized${NC}"
else
    echo -e "${GREEN}✅ Azure Developer CLI already initialized${NC}"
fi

# Provision Azure Resources
echo -e "\n${YELLOW}[3/5] Provisioning Azure resources (this may take 15-20 minutes)...${NC}"

ENV_NAME=${1:-prod}
azd config set DEFAULTS_ENV_NAME $ENV_NAME

echo -e "${BLUE}Environment: $ENV_NAME${NC}"
echo -e "${BLUE}This will deploy:${NC}"
echo "  • Azure OpenAI Service (with gpt-4o, text-embedding-3-large)"
echo "  • Azure AI Search (with vector search enabled)"
echo "  • Azure Storage Account"
echo "  • Azure Document Intelligence"
echo "  • Azure Application Insights"
echo "  • Optional: Azure Vision, Speech Services"

read -p "Continue with provisioning? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

azd provision

echo -e "${GREEN}✅ Azure resources provisioned${NC}"

# Load environment variables
echo -e "\n${YELLOW}[4/5] Loading environment variables...${NC}"

if [ -f ".azure/$ENV_NAME/.env" ]; then
    export $(cat ".azure/$ENV_NAME/.env" | xargs)
    echo -e "${GREEN}✅ Environment variables loaded${NC}"
else
    echo -e "${RED}❌ Environment file not found: .azure/$ENV_NAME/.env${NC}"
    exit 1
fi

# Deploy application code
echo -e "\n${YELLOW}[5/5] Deploying application code...${NC}"

azd deploy

echo -e "${GREEN}✅ Application deployed${NC}"

# Display important information
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${YELLOW}Important Information:${NC}"
echo -e "Environment: ${BLUE}$ENV_NAME${NC}"
echo -e "Resource Group: ${BLUE}${AZURE_RESOURCE_GROUP}${NC}"
echo -e "Location: ${BLUE}${AZURE_LOCATION}${NC}"
echo ""
echo -e "Service Endpoints:"
echo -e "  Azure OpenAI: ${BLUE}${AZURE_OPENAI_ENDPOINT}${NC}"
echo -e "  Azure Search: ${BLUE}${AZURE_SEARCH_ENDPOINT}${NC}"
echo -e "  Storage Account: ${BLUE}${AZURE_STORAGE_ENDPOINT}${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Deploy OpenAI model deployments (if not auto-deployed):"
echo "   az cognitiveservices account deployment create \\"
echo "     --resource-group \$AZURE_RESOURCE_GROUP \\"
echo "     --name \$AZURE_OPENAI_SERVICE \\"
echo "     --deployment-name gpt-4o \\"
echo "     --model-name gpt-4o \\"
echo "     --model-version 2024-05-13 \\"
echo "     --sku Standard --capacity 100"
echo ""
echo "2. Load sample documents:"
echo "   ./scripts/prepdocs.sh"
echo ""
echo "3. Test the application:"
echo "   ./app/start.sh"
echo ""
echo "4. Access the app at: http://localhost:5000"
echo ""
echo -e "${YELLOW}Foundry Integration:${NC}"
echo "5. Configure Foundry agents:"
echo "   az foundry project create --name azure-rag-system --location \$AZURE_LOCATION"
echo "   az foundry knowledge-base register --project azure-rag-system \\"
echo "     --index \$AZURE_SEARCH_INDEX --endpoint \$AZURE_SEARCH_ENDPOINT"
echo ""

echo -e "${GREEN}🎉 Your AI-powered RAG system is ready!${NC}"
