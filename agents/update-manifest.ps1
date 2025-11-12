# PowerShell script to update copilot-plugin-manifest.json with production URL

param(
    [Parameter(Mandatory=$true)]
    [string]$ProductionUrl
)

$manifestPath = Join-Path $PSScriptRoot "copilot-plugin-manifest.json"

if (-not (Test-Path $manifestPath)) {
    Write-Host "[ERROR] Manifest file not found: $manifestPath" -ForegroundColor Red
    exit 1
}

Write-Host "Updating manifest with production URL: $ProductionUrl" -ForegroundColor Cyan

# Read manifest
$manifestContent = Get-Content $manifestPath -Raw

# Remove trailing slash if present
$ProductionUrl = $ProductionUrl.TrimEnd('/')

# Replace all instances of your-domain.com
$manifestContent = $manifestContent -replace 'https://your-domain\.com', $ProductionUrl

# Write back
Set-Content -Path $manifestPath -Value $manifestContent -NoNewline

Write-Host "[OK] Manifest updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Updated endpoints:" -ForegroundColor Cyan
Write-Host "- Search: $ProductionUrl/api/copilot/search" -ForegroundColor White
Write-Host "- Query: $ProductionUrl/api/copilot/query" -ForegroundColor White
Write-Host "- Health: $ProductionUrl/api/copilot/health" -ForegroundColor White
Write-Host "- Icon: $ProductionUrl/icons/copilot-icon.png" -ForegroundColor White





