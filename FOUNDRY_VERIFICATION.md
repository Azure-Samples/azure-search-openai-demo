# Configuration Verification & Quick Start Guide

## Pre-Deployment Checklist

### 1. Prerequisites ✓
- [ ] Azure CLI installed: `az --version`
- [ ] Azure Developer CLI installed: `azd --version`
- [ ] Active Azure subscription with Owner/Contributor role
- [ ] Git repository cloned: `git clone https://github.com/Azure-Samples/azure-search-openai-demo.git`
- [ ] Python 3.10+ with Node.js 20+

### 2. Configuration Files ✓
- [ ] Created `.env` from `.env.template`
- [ ] Filled in all required Azure resource names
- [ ] Stored sensitive keys securely (Azure Key Vault)

## Deployment Steps

### Step 1: Initialize Azure Developer CLI
```bash
cd azure-search-openai-demo
azd init -t ./
```

### Step 2: Provision Azure Resources
```bash
# This takes 15-25 minutes
./scripts/setup-foundry-azure.sh prod

# Alternative: Manual steps
azd config set DEFAULTS_ENV_NAME prod
azd provision
```

### Step 3: Deploy OpenAI Models
```bash
# After provision completes, deploy model endpoints
./scripts/deploy-openai-models.sh

# Verify deployments
az cognitiveservices account deployment list \
  --resource-group $(az deployment group show -n --query properties.outputs.resourceGroupName -o tsv) \
  --name $AZURE_OPENAI_SERVICE
```

### Step 4: Deploy Application
```bash
azd deploy
```

### Step 5: Load Sample Data
```bash
# Download and index sample documents
./scripts/prepdocs.sh
```

## Configuration Verification

### Verify Azure OpenAI
```bash
# Test connectivity
curl -X GET \
  -H "api-key: $AZURE_OPENAI_KEY" \
  "$AZURE_OPENAI_ENDPOINT/openai/models?api-version=2024-08-01-preview"

# Expected response includes:
# - gpt-4o deployment
# - text-embedding-3-large deployment
```

### Verify Azure Search
```bash
# Check search indexes
curl -X GET \
  -H "api-key: $AZURE_SEARCH_KEY" \
  "$AZURE_SEARCH_ENDPOINT/indexes"

# Expected response includes:
# - gptkbindex (main index with vector fields)
```

### Verify Models Loaded Correctly
```bash
# Test gpt-4o
python -c "
from azure.openai import AzureOpenAI
client = AzureOpenAI(
    api_key='$AZURE_OPENAI_KEY',
    api_version='2024-08-01-preview',
    azure_endpoint='$AZURE_OPENAI_ENDPOINT'
)
response = client.chat.completions.create(
    model='gpt-4o',
    messages=[{'role': 'user', 'content': 'Say hello!'}],
    max_tokens=50
)
print(response.choices[0].message.content)
"

# Test embeddings
python -c "
from azure.openai import AzureOpenAI
client = AzureOpenAI(
    api_key='$AZURE_OPENAI_KEY',
    api_version='2024-08-01-preview',
    azure_endpoint='$AZURE_OPENAI_ENDPOINT'
)
response = client.embeddings.create(
    input='test text',
    model='text-embedding-3-large'
)
print(f'Embedding dimensions: {len(response.data[0].embedding)}')
"
```

### Verify Foundry Integration
```bash
# Check Foundry CLI
az foundry project list

# Create test agent (optional)
az foundry agent create \
  --agent-name test-rag-agent \
  --agent-description "Test RAG agent" \
  --deployment-type managed
```

### Verify Application
```bash
# Start development server
./app/start.sh

# Or manually start frontend and backend
cd app/frontend && npm run dev
# In another terminal:
cd app/backend && python -m quart run --reload -p 50505
```

### Verify End-to-End
```bash
# Open browser and navigate to
http://localhost:5000

# Test the chat interface:
# 1. Ask a question about company benefits
# 2. Verify response includes citations
# 3. Check "Show thought process" for reasoning
# 4. Enable "Streaming" to see real-time responses
```

## Health Check Dashboard

### Application Insights Monitoring
```bash
# View recent errors
az monitor app-insights query \
  --app $AZURE_APPINSIGHTS_NAME \
  --analytics-query "exceptions | limit 10"

# View dependency failures
az monitor app-insights query \
  --app $AZURE_APPINSIGHTS_NAME \
  --analytics-query "dependencies | where success == false | limit 10"

# View custom events (embeddings, searches)
az monitor app-insights query \
  --app $AZURE_APPINSIGHTS_NAME \
  --analytics-query "customEvents | limit 20"
```

### Performance Metrics
```bash
# Check OpenAI API performance
az monitor app-insights query \
  --app $AZURE_APPINSIGHTS_NAME \
  --analytics-query "pageViews | where name == 'POST /chat' | project duration, timestamp"

# Check search latency
az monitor app-insights query \
  --app $AZURE_APPINSIGHTS_NAME \
  --analytics-query "dependencies | where name == 'Search.Query' | project duration"
```

## Troubleshooting

### Issue: "Model not found" error
**Solution:**
```bash
# Verify model deployment names match environment variables
az cognitiveservices account deployment list \
  --resource-group $AZURE_OPENAI_RESOURCE_GROUP \
  --name $AZURE_OPENAI_SERVICE \
  --query "[].name" -o tsv

# Update environment variables to match deployment names
export AZURE_OPENAI_DEPLOYMENT_CHATGPT=gpt-4o
export AZURE_OPENAI_DEPLOYMENT_EMB=text-embedding-3-large
```

### Issue: Vector search returns no results
**Solution:**
```bash
# Verify embeddings dimensions match
# text-embedding-3-large should be 1536 dimensions
export AZURE_OPENAI_EMB_DIMENSIONS=1536

# Rebuild index if needed
./scripts/prepdocs.sh --clear-index
./scripts/prepdocs.sh
```

### Issue: Authentication failures
**Solution:**
```bash
# Verify credentials
az account show

# Re-authenticate if needed
az logout
az login

# Check Key Vault access
az keyvault secret show --vault-name $AZURE_KEYVAULT_NAME --name openai-key
```

### Issue: High latency or timeouts
**Solution:**
```bash
# Check Azure OpenAI quota/rate limits
az cognitiveservices account usage list \
  --name $AZURE_OPENAI_SERVICE \
  --resource-group $AZURE_OPENAI_RESOURCE_GROUP

# Reduce batch sizes if experiencing throttling
export OPENAI_EMBEDDING_BATCH_SIZE=50
export SEARCH_BATCH_SIZE=25
```

## Performance Optimization

### For Production Deployments
```bash
# Enable caching
export ENABLE_EMBEDDING_CACHE=true
export ENABLE_SEARCH_CACHE=true
export CACHE_TTL_HOURS=24

# Optimize container resources
export AZURE_CONTAINER_CPU=4
export AZURE_CONTAINER_MEMORY=8Gi

# Enable semantic ranking
export AZURE_SEARCH_SEMANTIC_CONFIGURATION=my-semantic-config

# Use higher quality embeddings
export AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-3-large
```

### For Cost Optimization
```bash
# Use gpt-4-mini for less critical queries
export AZURE_OPENAI_MINI_MODEL=gpt-4-mini

# Limit search results
export AZURE_VECTOR_SEARCH_K=3
export MAX_SEARCH_RESULTS=50

# Use text-embedding-3-small for initial filtering
export AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-3-small
export AZURE_OPENAI_EMB_DIMENSIONS=1536
```

## Next Steps After Setup

1. **Add Custom Data**
   ```bash
   # Place documents in ./data/
   ./scripts/prepdocs.sh
   ```

2. **Customize Prompts**
   - Edit system prompts in `app/backend/approaches/prompts/`
   - Tune temperature and max_tokens

3. **Enable Advanced Features**
   - Multimodal: `export ENABLE_MULTIMODAL=true`
   - Query rewriting: `export ENABLE_QUERY_REWRITING=true`
   - Advanced reasoning: `export DEFAULT_REASONING_EFFORT=high`

4. **Set Up Monitoring**
   - Configure alerts in Application Insights
   - Set up dashboards for key metrics

5. **Deploy to Production**
   ```bash
   azd deploy
   # Application will be available at:
   # https://<container-app-url>
   ```

## Useful Commands

```bash
# Show deployment details
azd show

# Get Azure resource info
az resource list --resource-group $AZURE_RESOURCE_GROUP

# View logs
azd monitor --follow

# List environment variables
azd env list-values

# Update single resource
azd provision <resource-name>

# Clean up (delete all resources)
azd down
```

## Security Best Practices

- ✅ Store all keys in Azure Key Vault (not in .env)
- ✅ Use managed identities for service-to-service auth
- ✅ Enable RBAC on all resources
- ✅ Use private endpoints for network isolation
- ✅ Enable audit logging in Application Insights
- ✅ Rotate keys regularly
- ✅ Use separate resource groups for dev/staging/prod

## Support & Documentation

- **Azure Documentation**: https://learn.microsoft.com/azure/
- **Azure OpenAI**: https://learn.microsoft.com/azure/ai-services/openai/
- **Azure Search**: https://learn.microsoft.com/azure/search/
- **Foundry**: https://learn.microsoft.com/foundry/
- **GitHub Issues**: https://github.com/Azure-Samples/azure-search-openai-demo/issues
