# Deployment Guide - Azure Search & OpenAI Demo

This guide covers deploying the RAG application to Azure using GitHub Actions and Bicep infrastructure.

## Prerequisites

- Azure subscription with sufficient permissions
- GitHub repository with admin access
- Docker installed (for local testing)
- Azure CLI installed

## Quick Start

### 1. Set Up Azure Resources

```bash
# Login to Azure
az login

# Set variables
export RESOURCE_GROUP="rg-azure-search-demo"
export LOCATION="eastus"
export STORAGE_ACCOUNT="stazuresearchdemo"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Deploy infrastructure using Bicep
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters location=$LOCATION
```

### 2. Configure GitHub Secrets

Navigate to **Settings → Secrets and variables → Actions** and add:

```
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP=<your-resource-group>
AZURE_LOCATION=<your-location>
AZURE_CREDENTIALS=<service-principal-json>
AZURE_STATIC_WEB_APPS_API_TOKEN=<swa-deployment-token>
```

#### Create Service Principal for GitHub Actions

```bash
az ad sp create-for-rbac \
  --name "github-actions-${RANDOM}" \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv) \
  --json-auth
```

Copy the output JSON to `AZURE_CREDENTIALS` secret.

### 3. Deploy via GitHub Actions

The deployment is triggered automatically on push to `main`:

```bash
git push origin main
```

Monitor deployment in **Actions** tab.

## Local Development

### Using Docker Compose

```bash
# Copy environment file
cp .env.example .env

# Update with your Azure credentials
nano .env

# Build and run
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
```

### Without Docker

**Backend:**
```bash
cd app/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Frontend:**
```bash
cd app/frontend
npm install
npm run dev
```

## Deployment Architecture

```
GitHub Repository
        ↓
GitHub Actions (CI/CD)
        ↓
    ├─→ Build & Test
    ├─→ Docker Build
    └─→ Push to GHCR
        ↓
    Azure Container Registry
        ↓
    ├─→ Deploy Backend (Container Instances/App Service)
    ├─→ Deploy Frontend (Static Web Apps)
    └─→ Configure Services
        ↓
    Azure AI Search
    Azure OpenAI
    Azure Blob Storage
    Azure Document Intelligence
```

## Monitoring & Logging

### View Deployment Logs

```bash
# Check deployment status
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main

# View application logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name azure-search-backend
```

### Application Insights

Logs are automatically sent to Application Insights. View in Azure Portal:
- **Resource Group** → **Application Insights** → **Logs**

## Environment Variables

Required environment variables for deployment:

| Variable | Description | Example |
|----------|-------------|---------|
| AZURE_SEARCH_SERVICE | Search service name | `my-search-service` |
| AZURE_SEARCH_INDEX | Search index name | `documents` |
| AZURE_OPENAI_ENDPOINT | OpenAI endpoint | `https://*.openai.azure.com/` |
| AZURE_OPENAI_KEY | OpenAI API key | `sk-...` |
| AZURE_OPENAI_DEPLOYMENT | Deployment name | `gpt-4` |
| AZURE_STORAGE_ACCOUNT | Storage account name | `mystorageaccount` |
| AZURE_DOCUMENT_INTELLIGENCE_SERVICE | Document Intelligence service | `my-doc-intel` |

## Scaling Considerations

### Horizontal Scaling
- **Backend**: Configure App Service Plan to multiple instances
- **Frontend**: Automatically handled by Azure Static Web Apps CDN

### Performance Optimization
- Enable Azure Cache for Redis for search result caching
- Configure blob storage lifecycle policies
- Use Azure CDN for frontend assets

## Cost Optimization

1. **Auto-scaling policies** for App Service
2. **Reserved instances** for predictable workloads
3. **Spot VMs** for non-critical environments
4. **Blob Storage tiers** based on access patterns

## Rollback Strategy

### Manual Rollback

```bash
# Redeploy previous version
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters imageName=ghcr.io/user/repo:previous-tag
```

### Automatic Rollback

Modify GitHub Actions workflow to revert on deployment failure.

## Troubleshooting

### Deployment Fails

1. Check GitHub Actions logs
2. Verify Azure credentials in secrets
3. Confirm resource group exists
4. Review Bicep template syntax

### Application Issues

```bash
# Check container status
az container show \
  --resource-group $RESOURCE_GROUP \
  --name azure-search-backend

# View recent logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name azure-search-backend \
  --tail 50
```

### Performance Issues

- Monitor Application Insights metrics
- Check Azure Search query latency
- Review OpenAI API response times
- Analyze blob storage access patterns

## Security Best Practices

1. ✅ Use Managed Identities for Azure services
2. ✅ Store secrets in GitHub Secrets, never in code
3. ✅ Enable Azure Policy for governance
4. ✅ Use private endpoints for sensitive services
5. ✅ Rotate credentials regularly
6. ✅ Enable audit logging for all services

## Next Steps

- [Azure Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Container Instances](https://learn.microsoft.com/en-us/azure/container-instances/)
- [Azure Static Web Apps](https://learn.microsoft.com/en-us/azure/static-web-apps/)

## Support

For issues or questions:
1. Check GitHub Issues
2. Review deployment logs
3. Contact Azure Support
