#!/bin/bash

# Switch to PatentsBERTa Embeddings
# This script configures the environment to use PatentsBERTa instead of Azure OpenAI embeddings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Switching to PatentsBERTa Embeddings${NC}"

# Check if azd is installed
if ! command -v azd &> /dev/null; then
    echo -e "${RED}❌ Azure Developer CLI (azd) is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if PatentsBERTa endpoint is available
PATENTSBERTA_ENDPOINT=$(azd env get-value PATENTSBERTA_ENDPOINT 2>/dev/null || echo "")

if [ -z "$PATENTSBERTA_ENDPOINT" ]; then
    echo -e "${RED}❌ PatentsBERTa endpoint not found. Please deploy the service first using:${NC}"
    echo "   ./scripts/deploy-patentsberta.sh"
    exit 1
fi

echo -e "${YELLOW}📋 Current PatentsBERTa endpoint: $PATENTSBERTA_ENDPOINT${NC}"

# Backup current configuration
echo -e "${YELLOW}💾 Backing up current configuration...${NC}"
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"

# Save current environment variables
azd env get-values > "$BACKUP_FILE"
echo -e "${GREEN}✅ Configuration backed up to: $BACKUP_FILE${NC}"

# Configure environment for PatentsBERTa
echo -e "${YELLOW}⚙️  Configuring environment for PatentsBERTa...${NC}"

# Set the OpenAI host to use PatentsBERTa
azd env set OPENAI_HOST "patentsberta"

# Set embedding dimensions for PatentsBERTa (768 dimensions)
azd env set AZURE_OPENAI_EMB_DIMENSIONS "768"

# Set the embedding model name
azd env set AZURE_OPENAI_EMB_MODEL_NAME "PatentSBERTa"

# Set the embedding field name (use a different field to avoid conflicts)
azd env set AZURE_SEARCH_FIELD_NAME_EMBEDDING "embedding_patentsberta"

echo -e "${GREEN}✅ Environment configured for PatentsBERTa${NC}"

# Test the PatentsBERTa service
echo -e "${YELLOW}🧪 Testing PatentsBERTa service...${NC}"

# Test health endpoint
if curl -f -s "$PATENTSBERTA_ENDPOINT/health" > /dev/null; then
    echo -e "${GREEN}✅ PatentsBERTa service is healthy${NC}"
else
    echo -e "${RED}❌ PatentsBERTa service is not responding. Please check the deployment.${NC}"
    exit 1
fi

# Warn about index recreation
echo -e "${YELLOW}⚠️  IMPORTANT: Search index needs to be recreated${NC}"
echo ""
echo -e "${RED}🚨 The search index must be deleted and recreated with new embedding dimensions.${NC}"
echo -e "${RED}   This will remove all existing indexed documents.${NC}"
echo ""

read -p "Do you want to delete the current search index? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗑️  Deleting current search index...${NC}"
    
    SEARCH_SERVICE=$(azd env get-value AZURE_SEARCH_SERVICE)
    SEARCH_INDEX=$(azd env get-value AZURE_SEARCH_INDEX)
    SEARCH_KEY=$(azd env get-value AZURE_SEARCH_KEY 2>/dev/null || echo "")
    
    if [ -n "$SEARCH_KEY" ]; then
        # Use API key if available
        curl -X DELETE \
            "https://${SEARCH_SERVICE}.search.windows.net/indexes/${SEARCH_INDEX}?api-version=2024-07-01" \
            -H "api-key: ${SEARCH_KEY}" \
            -w "HTTP Status: %{http_code}\n"
    else
        echo -e "${YELLOW}⚠️  No search key found. You may need to delete the index manually or use Azure CLI:${NC}"
        echo "   az search index delete --service-name $SEARCH_SERVICE --name $SEARCH_INDEX"
    fi
    
    echo -e "${GREEN}✅ Search index deletion initiated${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping index deletion. You'll need to delete it manually before reindexing.${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Successfully switched to PatentsBERTa embeddings!${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Wait for the search index to be fully deleted (if you chose to delete it)"
echo "2. Reindex your documents with PatentsBERTa embeddings:"
echo "   cd app/backend && python prepdocs.py '../../data/*'"
echo "3. Test the search functionality with patent-specific queries"
echo "4. Run the test suite to validate the integration:"
echo "   python tests/test-patentsberta.py"
echo ""
echo -e "${GREEN}🔗 PatentsBERTa Service Endpoints:${NC}"
echo "  Health: $PATENTSBERTA_ENDPOINT/health"
echo "  Info: $PATENTSBERTA_ENDPOINT/info"
echo "  Embeddings: $PATENTSBERTA_ENDPOINT/embeddings"
echo ""
echo -e "${YELLOW}💡 To switch back to Azure OpenAI embeddings, restore from backup:${NC}"
echo "   azd env set-values < $BACKUP_FILE"
