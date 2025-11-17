# Install Azure CLI on Windows
# Run this in PowerShell as Administrator

Write-Host "Installing Azure CLI..." -ForegroundColor Yellow

# Method 1: Using winget (Windows 10/11)
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "Using winget to install Azure CLI..." -ForegroundColor Cyan
    winget install -e --id Microsoft.AzureCLI
} 
# Method 2: Using MSI installer
else {
    Write-Host "Downloading Azure CLI MSI installer..." -ForegroundColor Cyan
    $installerUrl = "https://aka.ms/installazurecliwindows"
    $installerPath = "$env:TEMP\AzureCLI.msi"
    
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    
    Write-Host "Installing Azure CLI (this may take a few minutes)..." -ForegroundColor Cyan
    Start-Process msiexec.exe -ArgumentList "/i `"$installerPath`" /quiet" -Wait
    
    Remove-Item $installerPath
}

Write-Host ""
Write-Host "Azure CLI installation complete!" -ForegroundColor Green
Write-Host "Please close and reopen PowerShell, then run: az login" -ForegroundColor Yellow


