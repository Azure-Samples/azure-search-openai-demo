# Quick Docker Deployment Script for Agents Service
param(
    [string]$ACR_NAME = "devacr45mvbqy3dhymq",
    [string]$AGENTS_SERVICE = "app-agents-45mvbqy3dhymq",
    [string]$RESOURCE_GROUP = "AI-master-engineer",
    [string]$IMAGE_TAG = "latest"
)

Write-Host "=== Quick Docker Deployment ===" -ForegroundColor Green
Write-Host "ACR: $ACR_NAME" -ForegroundColor Cyan
Write-Host "App Service: $AGENTS_SERVICE" -ForegroundColor Cyan
Write-Host "Resource Group: $RESOURCE_GROUP" -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Azure CLI (az) is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Azure CLI:" -ForegroundColor Yellow
    Write-Host "1. Run: .\install-azure-cli.ps1 (as Administrator)" -ForegroundColor White
    Write-Host "2. Or download from: https://aka.ms/installazurecliwindows" -ForegroundColor White
    Write-Host "3. After installation, close and reopen PowerShell" -ForegroundColor White
    Write-Host "4. Run: az login" -ForegroundColor White
    Write-Host ""
    Write-Host "Alternatively, you can use Azure Portal to:" -ForegroundColor Yellow
    Write-Host "- Create ACR manually" -ForegroundColor White
    Write-Host "- Build and push images using ACR's 'Build' feature" -ForegroundColor White
    Write-Host "- Configure App Service container settings in Portal" -ForegroundColor White
    exit 1
}

# Check if we're in the agents directory
if (-not (Test-Path "Dockerfile")) {
    Write-Host "ERROR: Dockerfile not found. Please run this script from the agents/ directory." -ForegroundColor Red
    exit 1
}

# Step 1: Build and push
Write-Host "Step 1: Building and pushing image to ACR..." -ForegroundColor Yellow
az acr build `
  --registry $ACR_NAME `
  --image agents-service:$IMAGE_TAG `
  --file Dockerfile `
  .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to build and push image." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Image built and pushed successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Configure App Service
Write-Host "Step 2: Configuring App Service to use Docker image..." -ForegroundColor Yellow
$ACR_LOGIN_SERVER = "$ACR_NAME.azurecr.io"
$IMAGE_NAME = "$ACR_LOGIN_SERVER/agents-service:$IMAGE_TAG"

az webapp config container set `
  --name $AGENTS_SERVICE `
  --resource-group $RESOURCE_GROUP `
  --docker-custom-image-name $IMAGE_NAME `
  --docker-registry-server-url "https://$ACR_LOGIN_SERVER"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to configure App Service." -ForegroundColor Red
    exit 1
}

Write-Host "✅ App Service configured" -ForegroundColor Green
Write-Host ""

# Step 3: Grant ACR access (using Managed Identity)
Write-Host "Step 3: Granting ACR access to App Service..." -ForegroundColor Yellow

# Check if managed identity is enabled
$identity = az webapp identity show --name $AGENTS_SERVICE --resource-group $RESOURCE_GROUP --query "type" -o tsv
if ($identity -ne "SystemAssigned") {
    Write-Host "Enabling managed identity..." -ForegroundColor Yellow
    az webapp identity assign --name $AGENTS_SERVICE --resource-group $RESOURCE_GROUP
}

$PRINCIPAL_ID = az webapp identity show `
  --name $AGENTS_SERVICE `
  --resource-group $RESOURCE_GROUP `
  --query principalId -o tsv

if ([string]::IsNullOrEmpty($PRINCIPAL_ID)) {
    Write-Host "WARNING: Could not get managed identity. You may need to grant ACR access manually." -ForegroundColor Yellow
} else {
    $ACR_ID = az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query id -o tsv
    
    # Check if role assignment already exists
    $existing = az role assignment list --scope $ACR_ID --assignee $PRINCIPAL_ID --query "[?roleDefinitionName=='AcrPull']" -o tsv
    if ([string]::IsNullOrEmpty($existing)) {
        az role assignment create `
          --assignee $PRINCIPAL_ID `
          --role AcrPull `
          --scope $ACR_ID `
          --output none
        
        Write-Host "✅ ACR access granted" -ForegroundColor Green
    } else {
        Write-Host "✅ ACR access already granted" -ForegroundColor Green
    }
}
Write-Host ""

# Step 4: Restart App Service
Write-Host "Step 4: Restarting App Service..." -ForegroundColor Yellow
az webapp restart --name $AGENTS_SERVICE --resource-group $RESOURCE_GROUP

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to restart App Service." -ForegroundColor Red
    exit 1
}

Write-Host "✅ App Service restarted" -ForegroundColor Green
Write-Host ""

# Step 5: Get App URL
$APP_URL = az webapp show --name $AGENTS_SERVICE --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv

Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "App URL: https://$APP_URL" -ForegroundColor Cyan
Write-Host "Health Check: https://$APP_URL/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Check logs: az webapp log tail --name $AGENTS_SERVICE --resource-group $RESOURCE_GROUP" -ForegroundColor White
Write-Host "2. Test health: Invoke-WebRequest -Uri 'https://$APP_URL/'" -ForegroundColor White
Write-Host "3. Verify Docker config: az webapp config container show --name $AGENTS_SERVICE --resource-group $RESOURCE_GROUP" -ForegroundColor White

