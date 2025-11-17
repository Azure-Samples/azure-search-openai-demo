# PowerShell script to build and deploy agents service using Docker
# This script builds a Docker image and deploys it to Azure App Service

param(
    [string]$ImageTag = "latest",
    [switch]$SkipBuild = $false
)

Write-Host "=== Agents Service Docker Deployment ===" -ForegroundColor Green

# Check if azd is available
if (-not (Get-Command azd -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Azure Developer CLI (azd) is not installed." -ForegroundColor Red
    exit 1
}

# Load environment variables
Write-Host "Loading environment variables..." -ForegroundColor Yellow
azd env refresh

# Get required environment variables
$RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP
$AGENTS_SERVICE_NAME = azd env get-value AZURE_AGENTS_SERVICE_NAME
$SUBSCRIPTION_ID = azd env get-value AZURE_SUBSCRIPTION_ID

# Try to get ACR name (may not exist if using App Service)
$ACR_NAME = azd env get-value AZURE_CONTAINER_REGISTRY_NAME -ErrorAction SilentlyContinue

if ([string]::IsNullOrEmpty($RESOURCE_GROUP) -or [string]::IsNullOrEmpty($AGENTS_SERVICE_NAME)) {
    Write-Host "ERROR: Required environment variables not found." -ForegroundColor Red
    Write-Host "Please ensure AZURE_RESOURCE_GROUP and AZURE_AGENTS_SERVICE_NAME are set." -ForegroundColor Yellow
    exit 1
}

Write-Host "Resource Group: $RESOURCE_GROUP" -ForegroundColor Cyan
Write-Host "Service Name: $AGENTS_SERVICE_NAME" -ForegroundColor Cyan
Write-Host "Image Tag: $ImageTag" -ForegroundColor Cyan

# Option 1: Build and push to ACR (if available)
if (-not [string]::IsNullOrEmpty($ACR_NAME)) {
    Write-Host "`nBuilding Docker image and pushing to Azure Container Registry..." -ForegroundColor Yellow
    
    if (-not $SkipBuild) {
        az acr build `
            --registry $ACR_NAME `
            --image agents-service:$ImageTag `
            --file Dockerfile `
            .
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to build and push Docker image." -ForegroundColor Red
            exit 1
        }
    }
    
    $IMAGE_NAME = "${ACR_NAME}.azurecr.io/agents-service:$ImageTag"
    Write-Host "Image: $IMAGE_NAME" -ForegroundColor Green
    
    # Configure App Service to use the Docker image
    Write-Host "`nConfiguring App Service to use Docker image..." -ForegroundColor Yellow
    az webapp config container set `
        --name $AGENTS_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP `
        --docker-custom-image-name $IMAGE_NAME `
        --docker-registry-server-url "https://${ACR_NAME}.azurecr.io"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to configure App Service." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`n✅ Docker deployment completed successfully!" -ForegroundColor Green
    Write-Host "App Service is now using Docker image: $IMAGE_NAME" -ForegroundColor Cyan
}
else {
    # Option 2: Build locally and deploy using azd (if ACR not available)
    Write-Host "`nACR not found. Building Docker image locally..." -ForegroundColor Yellow
    Write-Host "Note: For production, consider setting up Azure Container Registry." -ForegroundColor Yellow
    
    # Build image locally
    if (-not $SkipBuild) {
        docker build -t agents-service:$ImageTag .
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to build Docker image locally." -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "`nFor App Service Docker deployment, you need to:" -ForegroundColor Yellow
    Write-Host "1. Push the image to a container registry (Docker Hub, ACR, etc.)" -ForegroundColor Yellow
    Write-Host "2. Configure App Service to use the image from the registry" -ForegroundColor Yellow
    Write-Host "`nOr use: azd deploy --service agents (for ZIP deployment)" -ForegroundColor Cyan
}

Write-Host "`nDeployment script completed." -ForegroundColor Green


