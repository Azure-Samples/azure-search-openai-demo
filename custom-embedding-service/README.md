# PatentsBERTa Integration - Implementation Complete

This document summarizes the completed PatentsBERTa embedding integration for the AI Master Engineer application.

## 📁 Files Created/Modified

### Core Service Files
- `custom-embedding-service/app.py` - FastAPI service for PatentsBERTa embeddings
- `custom-embedding-service/requirements.txt` - Python dependencies
- `custom-embedding-service/Dockerfile` - Container configuration

### Backend Integration
- `app/backend/prepdocslib/patentsberta_embeddings.py` - Custom embedding class
- `app/backend/prepdocs.py` - Updated to support PatentsBERTa (modified)
- `app/backend/prepdocslib/searchmanager.py` - Updated for 768-dimensional embeddings (modified)

### Infrastructure
- `infra/modules/patentsberta.bicep` - Azure Container App configuration
- `infra/main.bicep` - Updated to include PatentsBERTa service (modified)

### Configuration & Scripts
- `.env.patentsberta.example` - Environment configuration template
- `scripts/deploy-patentsberta.sh` - Automated deployment script
- `scripts/switch-to-patentsberta.sh` - Environment switching script
- `scripts/test-patentsberta.py` - Comprehensive test suite

## 🚀 Deployment Instructions

### Prerequisites
1. Ensure `OPENAI_HOST=patentsberta` is set in your environment
2. Azure CLI logged in with appropriate permissions
3. Docker not required (uses Azure Container Registry build)
4. Generate a secure API key for PatentsBERTa authentication

### Step-by-Step Deployment

1. **Generate Secure API Key**
   ```bash
   # Generate a cryptographically secure API key
   API_KEY=$(openssl rand -base64 32)
   echo "Generated API Key: $API_KEY"
   
   # Set the API key in your environment
   azd env set PATENTSBERTA_API_KEY "$API_KEY"
   ```

2. **Build and Push Container to ACR**
   ```bash
   # Get your container registry name
   REGISTRY_NAME=$(az acr list --resource-group rg-ai-master-engineer --query "[0].name" -o tsv)
   
   # Build and push image
   cd custom-embedding-service
   az acr build --registry $REGISTRY_NAME --image patentsberta-embeddings:latest .
   cd ..
   ```

3. **Deploy Infrastructure**
   ```bash
   azd up --no-prompt
   ```

4. **Grant Container Registry Access** (if deployment fails)
   ```bash
   # Get container app identity
   PRINCIPAL_ID=$(az containerapp show --name patentsberta-* --resource-group rg-ai-master-engineer --query "identity.principalId" -o tsv)
   
   # Get registry resource ID
   REGISTRY_ID=$(az acr show --name $REGISTRY_NAME --resource-group rg-ai-master-engineer --query "id" -o tsv)
   
   # Grant AcrPull role
   az role assignment create --assignee $PRINCIPAL_ID --role AcrPull --scope $REGISTRY_ID
   
   # Retry deployment
   azd up --no-prompt
   ```

5. **Verify Deployment**
   ```bash
   # Get PatentsBERTa endpoint and API key
   ENDPOINT=$(azd env get-values | grep PATENTSBERTA_ENDPOINT | cut -d'=' -f2 | tr -d '"')
   API_KEY=$(azd env get-values | grep PATENTSBERTA_API_KEY | cut -d'=' -f2 | tr -d '"')
   
   # Test health (no auth required)
   curl "$ENDPOINT/health"
   
   # Test embeddings with API key
   curl -X POST "$ENDPOINT/embeddings" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $API_KEY" \
     -d '{"texts": ["semiconductor wafer processing"]}' | jq '.embeddings[0] | length'
   ```

6. **Reindex Documents** (if switching from existing deployment)
   ```bash
   # Process documents with PatentsBERTa embeddings
   cd app/backend
   python prepdocs.py '../../data/*'
   cd ../..
   
   # Or for specific document types
   python prepdocs.py '../../data/patents/*.pdf'
   ```

## 🧪 Testing

### Test the PatentsBERTa Service

#### Option 1: Comprehensive Test Suite

```bash
# Export environment variables from Azure deployment
export PATENTSBERTA_ENDPOINT=$(azd env get-values | grep PATENTSBERTA_ENDPOINT | cut -d'=' -f2 | tr -d '"')
export PATENTSBERTA_API_KEY=$(azd env get-values | grep PATENTSBERTA_API_KEY | cut -d'=' -f2- | tr -d '"')

# Run the full test suite (includes authentication test)
python tests/test-patentsberta.py
```

#### Option 2: Manual Testing with curl
```bash
# Get endpoint and API key from environment
ENDPOINT=$(azd env get-values | grep PATENTSBERTA_ENDPOINT | cut -d'=' -f2 | tr -d '"')
API_KEY=$(azd env get-values | grep PATENTSBERTA_API_KEY | cut -d'=' -f2- | tr -d '"')

# Test health (no auth required)
curl "$ENDPOINT/health"

# Test embeddings with API key (should return 768)
curl -X POST "$ENDPOINT/embeddings" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"texts": ["semiconductor wafer processing"]}' | jq '.embeddings[0] | length'

# Test info endpoint (no auth required)
curl "$ENDPOINT/info"

# Test authentication (should fail without API key)
curl -X POST "$ENDPOINT/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test"]}' | jq '.detail'
```

## ⚙️ Configuration

### Environment Variables
```bash
# Core PatentsBERTa configuration
OPENAI_HOST=patentsberta
PATENTSBERTA_ENDPOINT=https://your-endpoint.azurecontainerapps.io
PATENTSBERTA_API_KEY=your-secure-api-key-here  # Required for API authentication
AZURE_OPENAI_EMB_DIMENSIONS=768
AZURE_SEARCH_FIELD_NAME_EMBEDDING=embedding_patentsberta
```

### Key Features
- **768-dimensional embeddings** (vs 1536 for Azure OpenAI)
- **Patent-specific training** for better technical document understanding
- **Self-hosted** for cost control and customization
- **Auto-scaling** Container App deployment
- **Health monitoring** and performance testing
- **API key authentication** for secure access to embeddings endpoint

### Security
- **Protected /embeddings endpoint** with X-API-Key header authentication
- **Public health and info endpoints** for monitoring
- **No-op authentication** if PATENTSBERTA_API_KEY is not configured
- **Secure parameter handling** in Azure deployment

## 🔄 Switching Between Embedding Services

### Switch to PatentsBERTa
```bash
./scripts/switch-to-patentsberta.sh
```

### Switch Back to Azure OpenAI
```bash
# Restore from backup (created automatically)
azd env set-values < .env.backup.YYYYMMDD_HHMMSS
```

## 📊 Expected Benefits

### For Patent Documents
- **Better semantic understanding** of technical terminology
- **Improved similarity matching** for engineering concepts
- **Enhanced retrieval accuracy** for patent claims and specifications

### Cost & Control
- **Predictable costs** vs per-token pricing
- **Self-managed scaling** and performance tuning
- **Custom model updates** and fine-tuning capabilities

## 🔍 Architecture Overview

```
Document Processing → PatentsBERTa Service → Azure AI Search (768D)
User Queries → PatentsBERTa Service → Vector Search → Results
```

### Components
1. **PatentsBERTa Container App** - Hosts the embedding model
2. **Custom Embedding Class** - Integrates with existing backend
3. **Updated Search Index** - Supports 768-dimensional vectors
4. **Environment Configuration** - Switches between embedding services

## 🚨 Important Notes

### Index Recreation Required
- The search index must be recreated with new embedding dimensions
- All documents need to be reprocessed with PatentsBERTa embeddings
- Backup existing data if needed before switching

### Performance Considerations
- **Initial model loading** takes 2-3 minutes
- **First embedding request** may be slower due to model warmup
- **Batch processing** is more efficient than individual requests

### Monitoring
- Health endpoint: `/health`
- Model info: `/info`
- Application Insights integration for logging
- Container App metrics for scaling decisions

## 🛠️ Troubleshooting

### Common Issues

**Container Image Pull Failed**
```bash
# Grant managed identity access to ACR
PRINCIPAL_ID=$(az containerapp show --name patentsberta-* --resource-group rg-ai-master-engineer --query "identity.principalId" -o tsv)
REGISTRY_ID=$(az acr show --name YOUR_REGISTRY --resource-group rg-ai-master-engineer --query "id" -o tsv)
az role assignment create --assignee $PRINCIPAL_ID --role AcrPull --scope $REGISTRY_ID
```

**Bicep Template Error (openAiHost)**
- Ensure `infra/main.bicep` includes `patentsberta` in allowed values for `openAiHost` parameter

**Search Index Compression Error**
- Truncation dimension must be less than embedding dimensions (768)
- Fixed automatically in `searchmanager.py` with dynamic calculation

**Service Not Starting**
```bash
# Check container logs
az containerapp logs show --name patentsberta-* --resource-group rg-ai-master-engineer
```

**Memory Issues**
```bash
# Increase memory allocation
az containerapp update --name patentsberta-* --memory 8Gi
```

### Support Commands
```bash
# Get current environment status
azd env get-values | grep -E "(OPENAI_HOST|PATENTSBERTA|AZURE_OPENAI_EMB|AZURE_SEARCH_FIELD)"

# Test service health
ENDPOINT=$(azd env get-values | grep PATENTSBERTA_ENDPOINT | cut -d'=' -f2 | tr -d '"')
curl "$ENDPOINT/health"

# Check embedding dimensions
curl "$ENDPOINT/info"

# View container logs
az containerapp logs show --name patentsberta-* --resource-group rg-ai-master-engineer

# Monitor resource usage
az monitor metrics list --resource $(az containerapp show --name patentsberta-* --resource-group rg-ai-master-engineer --query "id" -o tsv)

# Check container app status
az containerapp show --name patentsberta-* --resource-group rg-ai-master-engineer --query "{name:name,status:properties.provisioningState,fqdn:properties.configuration.ingress.fqdn}"
```
