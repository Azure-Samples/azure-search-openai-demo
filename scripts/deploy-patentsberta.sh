#!/bin/bash

# Deploy PatentsBERTa Embedding Service
# This script builds and deploys the PatentsBERTa container to Azure Container Registry

set -e

# Default image tag - uses immutable versioning for deterministic deployments
# Format: v1.0.0-YYYYMMDD (can be overridden with IMAGE_TAG environment variable)
# This ensures reproducible deployments and allows for proper rollback capabilities
IMAGE_TAG=${IMAGE_TAG:-"v1.0.0-$(date +%Y%m%d)"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting PatentsBERTa Embedding Service Deployment${NC}"

# Check if azd is installed
if ! command -v azd &> /dev/null; then
    echo -e "${RED}❌ Azure Developer CLI (azd) is not installed. Please install it first.${NC}"
    exit 1
fi

# Load environment variables
echo -e "${YELLOW}📋 Loading environment variables...${NC}"
azd env refresh

# Get required environment variables
RESOURCE_GROUP=$(azd env get-value AZURE_RESOURCE_GROUP)
REGISTRY_ENDPOINT=$(azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT)
REGISTRY_NAME=$(echo $REGISTRY_ENDPOINT | cut -d'.' -f1)
SUBSCRIPTION_ID=$(azd env get-value AZURE_SUBSCRIPTION_ID)

if [ -z "$RESOURCE_GROUP" ] || [ -z "$REGISTRY_NAME" ] || [ -z "$SUBSCRIPTION_ID" ]; then
    echo -e "${RED}❌ Required environment variables not found. Please run 'azd up' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment variables loaded${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Registry: $REGISTRY_NAME"
echo "  Subscription: $SUBSCRIPTION_ID"
echo "  Image Tag: $IMAGE_TAG"

# Build and push the PatentsBERTa container
echo -e "${YELLOW}🔨 Building and pushing PatentsBERTa container...${NC}"

cd custom-embedding-service

# Build and push using Azure Container Registry
az acr build \
    --registry "$REGISTRY_NAME" \
    --image patentsberta-embeddings:$IMAGE_TAG \
    --file Dockerfile \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container built and pushed successfully${NC}"
else
    echo -e "${RED}❌ Failed to build and push container${NC}"
    exit 1
fi

cd ..

# Set environment variables for PatentsBERTa
echo -e "${YELLOW}⚙️  Configuring environment for PatentsBERTa...${NC}"

# Set the OpenAI host to use PatentsBERTa
azd env set OPENAI_HOST "patentsberta"

# Set embedding dimensions for PatentsBERTa (768 dimensions)
azd env set AZURE_OPENAI_EMB_DIMENSIONS "768"

# Set the embedding field name
azd env set AZURE_SEARCH_FIELD_NAME_EMBEDDING "embedding_patentsberta"

# Set the image tag for deployment
azd env set PATENTSBERTA_IMAGE_TAG "$IMAGE_TAG"

echo -e "${GREEN}✅ Environment configured for PatentsBERTa${NC}"

# Deploy the infrastructure
echo -e "${YELLOW}🏗️  Deploying infrastructure with PatentsBERTa service...${NC}"

azd up --no-prompt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
    
    # Get the PatentsBERTa endpoint
    PATENTSBERTA_ENDPOINT=$(azd env get-value PATENTSBERTA_ENDPOINT)
    
    if [ -n "$PATENTSBERTA_ENDPOINT" ]; then
        echo -e "${GREEN}🎉 PatentsBERTa service deployed successfully!${NC}"
        echo "  Endpoint: $PATENTSBERTA_ENDPOINT"
        
        # Test the service
        echo -e "${YELLOW}🧪 Testing PatentsBERTa service...${NC}"
        
        # Wait a moment for the service to be ready
        sleep 30
        
        # Test health endpoint
        if curl -f "$PATENTSBERTA_ENDPOINT/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ PatentsBERTa service is healthy${NC}"
        else
            echo -e "${YELLOW}⚠️  PatentsBERTa service may still be starting up. Check logs if issues persist.${NC}"
        fi
        
        # Test embedding endpoint
        echo -e "${YELLOW}🔍 Testing embedding generation...${NC}"
        curl -X POST "$PATENTSBERTA_ENDPOINT/embeddings" \
            -H "Content-Type: application/json" \
            -d '{"texts": ["structural engineering patent claim"], "normalize": true}' \
            --max-time 60 > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Embedding generation test successful${NC}"
        else
            echo -e "${YELLOW}⚠️  Embedding generation test failed. Service may still be loading the model.${NC}"
        fi
        
    else
        echo -e "${RED}❌ PatentsBERTa endpoint not found in environment${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Infrastructure deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 PatentsBERTa deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Wait for the PatentsBERTa model to fully load (may take 2-3 minutes)"
echo "2. Delete the existing search index to recreate with new dimensions:"
echo "   azd env get-value AZURE_SEARCH_SERVICE | xargs -I {} curl -X DELETE \"https://{}.search.windows.net/indexes/\$(azd env get-value AZURE_SEARCH_INDEX)?api-version=2024-07-01\" -H \"api-key: \$(azd env get-value AZURE_SEARCH_KEY)\""
echo "3. Run document processing to reindex with PatentsBERTa embeddings:"
echo "   python app/backend/prepdocs.py './data/*'"
echo "4. Test search quality with patent-specific queries"
echo ""
echo -e "${YELLOW}🏷️  Image Tag Management:${NC}"
echo "  Current tag: $IMAGE_TAG"
echo "  To deploy a specific version: IMAGE_TAG=v1.0.0-20241201 ./scripts/deploy-patentsberta.sh"
echo "  To rollback: Set PATENTSBERTA_IMAGE_TAG in azd environment and run 'azd up'"
echo ""
echo -e "${GREEN}🔗 Useful endpoints:${NC}"
echo "  Health: $PATENTSBERTA_ENDPOINT/health"
echo "  Info: $PATENTSBERTA_ENDPOINT/info"
echo "  Embeddings: $PATENTSBERTA_ENDPOINT/embeddings"
