## Set the preference to stop on the first error
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Loading azd .env file from current environment"
Write-Host ""

$output = azd env get-values

foreach ($line in $output) {
  if (!$line.Contains('=')) {
    continue
  }

  $name, $value = $line.Split("=")
  $value = $value -replace '^\"|\"$'
  [Environment]::SetEnvironmentVariable($name, $value)
}

Write-Host "Environment variables set."

if (-not $env:AZURE_USE_AUTHENTICATION) {
    exit 0
}

if ($env:AZURE_SERVER_APP_ID) {
    $output = az ad app show --id $env:AZURE_SERVER_APP_ID 2>&1
    if ($?) {
        $serverAppDetails = $output | ConvertFrom-Json
    } else {
        throw "Server app in AZURE_SERVER_APP_ID does not exist - $output"
    }
} else {
    $serverAppDisplayName = $env:AZURE_SERVER_DISPLAY_NAME
    if (-not $serverAppDisplayName) {
        $serverAppDisplayName = "azure-search-openai-demo-server"
    }

    $output = az ad app create --display-name $serverAppDisplayName --sign-in-audience AzureADMyOrg
    if ($?) {
        $serverAppDetails = $output | ConvertFrom-Json
    } else {
        throw "Server app cannot be created - $output"
    }
}
