# PowerShell script to help deploy Agents service to Azure
# Run this from the agents/ directory

Write-Host "==========================================="
Write-Host "Azure Deployment Helper for Agents Service"
Write-Host "==========================================="
Write-Host ""

# Check if Azure CLI is installed
try {
    $azVersion = az version
    Write-Host "[OK] Azure CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Azure CLI is not installed" -ForegroundColor Red
    Write-Host "Install from: https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    exit 1
}

# Check if logged in
try {
    $account = az account show 2>$null
    if ($account) {
        Write-Host "[OK] Logged into Azure" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Not logged in. Logging in..." -ForegroundColor Yellow
        az login
    }
} catch {
    Write-Host "[INFO] Logging into Azure..." -ForegroundColor Yellow
    az login
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan

# Get app name
$appName = Read-Host "Enter your App Service name (e.g., ai-master-engineer-agents)"
if ([string]::IsNullOrWhiteSpace($appName)) {
    Write-Host "[ERROR] App name is required" -ForegroundColor Red
    exit 1
}

# Get resource group
$resourceGroup = Read-Host "Enter resource group name (or 'new' to create one)"
if ($resourceGroup -eq "new") {
    $resourceGroup = "$appName-rg"
    Write-Host "[INFO] Will create resource group: $resourceGroup" -ForegroundColor Yellow
}

# Get region
$region = Read-Host "Enter region (e.g., eastus, westus2) [default: eastus]"
if ([string]::IsNullOrWhiteSpace($region)) {
    $region = "eastus"
}

Write-Host ""
Write-Host "Creating App Service..." -ForegroundColor Cyan

# Create resource group if needed
if ($resourceGroup -eq "$appName-rg") {
    Write-Host "Creating resource group: $resourceGroup" -ForegroundColor Yellow
    az group create --name $resourceGroup --location $region
}

# Create App Service
Write-Host "Creating App Service: $appName" -ForegroundColor Yellow
az webapp create `
    --resource-group $resourceGroup `
    --name $appName `
    --runtime "PYTHON:3.11" `
    --plan "$appName-plan" `
    --location $region

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to create App Service" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] App Service created" -ForegroundColor Green

# Get the URL
$appUrl = "https://$appName.azurewebsites.net"
Write-Host ""
Write-Host "Your App Service URL: $appUrl" -ForegroundColor Green

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Configure App Settings (environment variables)" -ForegroundColor Yellow
Write-Host "2. Deploy code (GitHub, VS Code, or Azure CLI)" -ForegroundColor Yellow
Write-Host "3. Update copilot-plugin-manifest.json with: $appUrl" -ForegroundColor Yellow

Write-Host ""
Write-Host "Configure App Settings now? (y/n)" -ForegroundColor Cyan
$configure = Read-Host
if ($configure -eq "y" -or $configure -eq "Y") {
    Write-Host ""
    Write-Host "Open Azure Portal to configure:" -ForegroundColor Yellow
    Write-Host "https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$resourceGroup/providers/Microsoft.Web/sites/$appName/configuration" -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "Add these settings (from agents/.env):" -ForegroundColor Yellow
    Write-Host "- MICROSOFT_APP_ID" -ForegroundColor White
    Write-Host "- MICROSOFT_APP_PASSWORD" -ForegroundColor White
    Write-Host "- AZURE_TENANT_ID" -ForegroundColor White
    Write-Host "- AZURE_CLIENT_ID" -ForegroundColor White
    Write-Host "- AZURE_CLIENT_SECRET" -ForegroundColor White
    Write-Host "- BACKEND_URL" -ForegroundColor White
}

Write-Host ""
Write-Host "Deploy code now? (y/n)" -ForegroundColor Cyan
$deploy = Read-Host
if ($deploy -eq "y" -or $deploy -eq "Y") {
    Write-Host ""
    Write-Host "Deploying via Azure CLI..." -ForegroundColor Yellow
    az webapp up --name $appName --resource-group $resourceGroup
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Deployment complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Test your deployment:" -ForegroundColor Cyan
        Write-Host "curl $appUrl/api/copilot/health" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "==========================================="
Write-Host "Don't forget to update copilot-plugin-manifest.json" -ForegroundColor Yellow
Write-Host "Replace 'your-domain.com' with: $appUrl" -ForegroundColor Yellow
Write-Host "==========================================="





