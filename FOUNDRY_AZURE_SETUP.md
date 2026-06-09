# Complete Azure Services + Foundry Setup Guide

**Project:** Azure Search OpenAI Demo with Foundry Integration  
**Date:** 2026-06-09  
**Status:** Comprehensive Configuration Setup

## Phase 1: Azure OpenAI Configuration (Latest Models)

### 1.1 Required Models

The latest recommended OpenAI models for this RAG application:

```bash
# Chat/Reasoning Models (Choose based on use case)
AZURE_OPENAI_CHATGPT_MODEL=gpt-4o              # Latest flagship multimodal model
# AZURE_OPENAI_CHATGPT_MODEL=gpt-4-turbo       # Fallback: Advanced reasoning
# AZURE_OPENAI_CHATGPT_MODEL=gpt-4-mini        # Cost-optimized: Fast processing

# Embedding Model (for vector search)
AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-3-large  # Latest embeddings (1536 dims)
AZURE_OPENAI_EMB_DIMENSIONS=1536

# Knowledge Base Model (if using agentic retrieval)
AZURE_OPENAI_KNOWLEDGEBASE_MODEL=gpt-4o
```

### 1.2 Azure Credentials & Endpoints

```bash
# Core Azure Setup
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP=<your-resource-group>
AZURE_LOCATION=eastus                          # Must support all services
AZURE_ENV_NAME=<environment-name>

# Azure OpenAI Service
AZURE_OPENAI_SERVICE=<openai-service-name>     # e.g., myorg-openai-prod
AZURE_OPENAI_RESOURCE_GROUP=<resource-group>   # Can be same as AZURE_RESOURCE_GROUP
AZURE_OPENAI_LOCATION=eastus                   # Use same as AZURE_LOCATION
AZURE_OPENAI_KEY=<service-key>                 # From Azure Portal
AZURE_OPENAI_ENDPOINT=https://<service>.openai.azure.com/

# Model Deployments (These must be created in Azure OpenAI Studio)
AZURE_OPENAI_DEPLOYMENT_CHATGPT=gpt-4o         # Deployment name for chat model
AZURE_OPENAI_DEPLOYMENT_EMB=text-embedding-3-large  # Deployment name for embeddings
```

### 1.3 Azure Search Configuration

```bash
# Azure AI Search (Vector + Full-text search)
AZURE_SEARCH_SERVICE=<search-service-name>     # e.g., myorg-search-prod
AZURE_SEARCH_RESOURCE_GROUP=<resource-group>
AZURE_SEARCH_LOCATION=eastus
AZURE_SEARCH_KEY=<admin-key>                   # From Azure Portal
AZURE_SEARCH_ENDPOINT=https://<service>.search.windows.net/
AZURE_SEARCH_INDEX=gptkbindex                  # Index name
AZURE_SEARCH_SEMANTIC_CONFIGURATION=my-semantic-config  # For semantic ranking

# Vector Search Settings
AZURE_USE_VECTOR_SEARCH=true                   # Enable vector/hybrid search
AZURE_USE_TEXT_SEARCH=true                     # Enable full-text fallback
AZURE_VECTOR_SEARCH_DIMENSIONS=1536            # Must match embedding dimensions
```

### 1.4 Storage & Data Services

```bash
# Azure Blob Storage (for documents & embeddings cache)
AZURE_STORAGE_ACCOUNT=<storage-account-name>
AZURE_STORAGE_RESOURCE_GROUP=<resource-group>
AZURE_STORAGE_CONTAINER=documents              # Main container for uploaded docs
AZURE_STORAGE_KEY=<storage-account-key>
AZURE_STORAGE_ENDPOINT=https://<account>.blob.core.windows.net/

# Azure Document Intelligence (PDF parsing & layout analysis)
AZURE_DOCUMENTINTELLIGENCE_SERVICE=<doc-intel-service>
AZURE_DOCUMENTINTELLIGENCE_KEY=<doc-intel-key>
AZURE_DOCUMENTINTELLIGENCE_ENDPOINT=https://<service>.cognitiveservices.azure.com/
AZURE_DOCUMENTINTELLIGENCE_LOCATION=eastus

# Optional: Azure Data Lake Gen2 (for cloud ingestion)
AZURE_ADLSGEN2_ACCOUNT=<datalake-account>
AZURE_ADLSGEN2_CONTAINER=source-data
AZURE_ADLSGEN2_KEY=<datalake-key>
```

### 1.5 Optional AI Services

```bash
# Azure Computer Vision (for image analysis in multimodal documents)
ENABLE_MULTIMODAL=true
AZURE_VISION_SERVICE=<vision-service-name>
AZURE_VISION_LOCATION=eastus
AZURE_VISION_KEY=<vision-key>

# Azure Content Understanding (advanced media description)
ENABLE_CONTENT_UNDERSTANDING=false             # Set to true if using media-heavy docs
AZURE_CONTENT_UNDERSTANDING_SERVICE=<cu-service>

# Azure Speech Services (accessibility features)
AZURE_SPEECH_SERVICE=<speech-service-name>
AZURE_SPEECH_SERVICE_LOCATION=eastus
AZURE_SPEECH_SERVICE_KEY=<speech-key>
AZURE_SPEECH_SERVICE_VOICE=en-US-AriaNeural
```

### 1.6 Monitoring & Logging

```bash
# Azure Application Insights (APM & observability)
AZURE_APPINSIGHTS_ENABLED=true
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=<key>;<endpoint>
AZURE_APPINSIGHTS_WORKSPACE_NAME=<workspace-name>
AZURE_LOG_ANALYTICS_WORKSPACE_ID=<workspace-id>

# Observability Settings
ENABLE_PERFORMANCE_TRACING=true
ENABLE_OPENAI_INSTRUMENTATION=true
LOG_LEVEL=INFO
```

## Phase 2: Microsoft Foundry Integration

### 2.1 Foundry Service Setup

```bash
# Microsoft Foundry Project
FOUNDRY_PROJECT_NAME=azure-rag-system
FOUNDRY_PROJECT_LOCATION=eastus
FOUNDRY_SUBSCRIPTION_ID=<same-as-AZURE_SUBSCRIPTION_ID>

# Foundry Credentials
FOUNDRY_API_KEY=<foundry-api-key>
FOUNDRY_API_ENDPOINT=https://api.foundry.microsoft.com/
FOUNDRY_WORKSPACE_ID=<workspace-id>
```

### 2.2 Agent Configuration

```bash
# Declarative Agents for Foundry
AGENT_NAME=rag-assistant
AGENT_DESCRIPTION=RAG-powered AI assistant with document search

# Agentic Retrieval Settings
ENABLE_AGENTIC_KNOWLEDGEBASE=true
ENABLE_AGENTIC_RETRIEVAL=true
ENABLE_QUERY_REWRITING=true                    # Improve search queries via LLM
ENABLE_STREAMING=true                          # Real-time response streaming

# Reasoning & Planning
DEFAULT_REASONING_EFFORT=medium                # Options: low, medium, high
ENABLE_ADVANCED_REASONING=true
```

### 2.3 Knowledge Base Integration

```bash
# Knowledge Base Configuration
KNOWLEDGEBASE_INDEX_NAME=gptkbindex-kb
KNOWLEDGEBASE_ENDPOINT=https://<foundry-kb>.microsoft.com/
KNOWLEDGEBASE_API_KEY=<kb-api-key>

# Data Sources
ENABLE_SHAREPOINT_SOURCE=false                 # Set true for SharePoint docs
ENABLE_WEB_SOURCE=false                        # Set true for web search
ENABLE_TEAMS_SOURCE=false                      # Set true for Teams messages
```

## Phase 3: Authentication & Security

### 3.1 Microsoft Entra ID (AAD)

```bash
# Entra ID App Registration
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<app-registration-id>
AZURE_CLIENT_SECRET=<app-secret>               # Store in Key Vault in production
AZURE_PRINCIPAL_ID=<service-principal-id>      # For RBAC

# Authentication Settings
AUTH_ENABLED=true
ENABLE_ENTRA_LOGIN=true
ENFORCE_ACCESS_CONTROL=true                    # Enable per-user access control
```

### 3.2 Key Vault (Secrets Management)

```bash
# Azure Key Vault
AZURE_KEYVAULT_NAME=<keyvault-name>
AZURE_KEYVAULT_ENDPOINT=https://<keyvault>.vault.azure.net/

# Secret References (use these in production, not inline keys)
AZURE_OPENAI_KEY_REF=kv://<key-name>
AZURE_SEARCH_KEY_REF=kv://<key-name>
AZURE_STORAGE_KEY_REF=kv://<key-name>
```

## Phase 4: Deployment Configuration

### 4.1 Container Deployment (Azure Container Apps)

```bash
# Container Registry
AZURE_REGISTRY_NAME=<registry-name>
AZURE_REGISTRY_LOCATION=eastus

# Container Apps Environment
AZURE_CONTAINER_APP_NAME=rag-app
AZURE_CONTAINER_ENV_NAME=rag-app-env
ENABLE_INGRESS=true
CONTAINER_PORT=8000
```

### 4.2 Infrastructure-as-Code

```bash
# Bicep Deployment Parameters
BICEP_TEMPLATE=infra/main.bicep
BICEP_PARAMS=infra/main.parameters.json

# Deployment Settings
DEPLOY_ENVIRONMENT=production                  # Options: dev, staging, production
AUTO_DEPLOY_UPDATES=true
```

## Setup Steps

### Step 1: Deploy Azure Resources

```bash
cd /path/to/azure-search-openai-demo
azd init                                        # Initialize Azure Developer CLI
azd config set DEFAULTS_ENV_NAME prod          # Set environment name
azd provision                                  # Deploy all resources
azd deploy                                     # Deploy application code
```

### Step 2: Create OpenAI Model Deployments

After provisioning, manually deploy models in Azure OpenAI Studio:

1. **Chat Model**: `gpt-4o` (deployment name: `gpt-4o`)
   - Tokens per minute (TPM): 100,000 (adjust based on quota)
   - Base model: gpt-4o
   
2. **Embedding Model**: `text-embedding-3-large` (deployment name: `text-embedding-3-large`)
   - Tokens per minute (TPM): 350,000
   - Base model: text-embedding-3-large
   - Dimensions: 1536

### Step 3: Configure Foundry Integration

```bash
# 1. Create Foundry project
az foundry project create \
  --name $FOUNDRY_PROJECT_NAME \
  --location $FOUNDRY_PROJECT_LOCATION

# 2. Register knowledge base
az foundry knowledge-base register \
  --project $FOUNDRY_PROJECT_NAME \
  --index $KNOWLEDGEBASE_INDEX_NAME \
  --endpoint $AZURE_SEARCH_ENDPOINT \
  --key $AZURE_SEARCH_KEY

# 3. Deploy agent
az foundry agent deploy \
  --project $FOUNDRY_PROJECT_NAME \
  --agent-name $AGENT_NAME \
  --agent-description $AGENT_DESCRIPTION
```

### Step 4: Load Sample Data

```bash
cd /path/to/azure-search-openai-demo
./scripts/prepdocs.sh
```

### Step 5: Verify Configuration

```bash
# Test Azure OpenAI connectivity
curl -X GET \
  -H "api-key: $AZURE_OPENAI_KEY" \
  "$AZURE_OPENAI_ENDPOINT/openai/models?api-version=2024-08-01-preview"

# Test Azure Search connectivity  
curl -X GET \
  -H "api-key: $AZURE_SEARCH_KEY" \
  "$AZURE_SEARCH_ENDPOINT/indexes"

# Test Foundry integration
az foundry agent test --project $FOUNDRY_PROJECT_NAME --agent-name $AGENT_NAME
```

## Environment File Template

Create `.env.production` with all variables above:

```bash
# Production Environment Configuration
# This file should be stored securely (e.g., Azure Key Vault)

# ===== Azure Core =====
AZURE_SUBSCRIPTION_ID=
AZURE_RESOURCE_GROUP=
AZURE_LOCATION=eastus
AZURE_ENV_NAME=prod

# ===== Azure OpenAI =====
AZURE_OPENAI_SERVICE=
AZURE_OPENAI_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_CHATGPT_MODEL=gpt-4o
AZURE_OPENAI_DEPLOYMENT_CHATGPT=gpt-4o
AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-3-large
AZURE_OPENAI_DEPLOYMENT_EMB=text-embedding-3-large
AZURE_OPENAI_EMB_DIMENSIONS=1536

# ===== Azure Search =====
AZURE_SEARCH_SERVICE=
AZURE_SEARCH_KEY=
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_INDEX=gptkbindex
AZURE_USE_VECTOR_SEARCH=true
AZURE_USE_TEXT_SEARCH=true

# ===== Storage =====
AZURE_STORAGE_ACCOUNT=
AZURE_STORAGE_KEY=
AZURE_STORAGE_CONTAINER=documents

# ===== Foundry =====
FOUNDRY_PROJECT_NAME=azure-rag-system
FOUNDRY_API_KEY=
ENABLE_AGENTIC_KNOWLEDGEBASE=true

# ===== Authentication =====
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AUTH_ENABLED=true

# ===== Features =====
ENABLE_MULTIMODAL=true
ENABLE_STREAMING=true
ENABLE_ADVANCED_REASONING=true
```

## Monitoring & Troubleshooting

### Health Checks

```bash
# Check deployed services
azd show                                       # Show current deployment status

# View Application Insights logs
az monitor app-insights query \
  --app $AZURE_APPINSIGHTS_NAME \
  --analytics-query "customEvents | limit 10"

# Check search index status
az search admin-key show --resource-group $AZURE_RESOURCE_GROUP \
  --service-name $AZURE_SEARCH_SERVICE
```

### Common Issues

| Issue | Solution |
|-------|----------|
| OpenAI deployment not found | Verify deployment names in Azure OpenAI Studio match environment variables |
| Vector search failing | Check embedding dimensions match (1536 for text-embedding-3-large) |
| Access denied | Verify RBAC roles: Owner or Contributor on subscription |
| Foundry agent not responding | Check agent is deployed: `az foundry agent list` |

## Next Steps

1. ✅ Deploy with `azd up`
2. ✅ Configure Foundry agents
3. ✅ Load sample documents via `scripts/prepdocs.sh`
4. ✅ Test chat interface at http://localhost:5000
5. ✅ Monitor with Application Insights
6. ✅ Set up CI/CD pipeline in GitHub Actions
