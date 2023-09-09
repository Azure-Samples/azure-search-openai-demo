## Set the preference to stop on the first error
$ErrorActionPreference = "Stop"

# Capture all arguments passed to the script
$scriptArgs = $args

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

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  # fallback to python3 if python not found
  $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

Write-Host 'Creating python virtual environment "scripts/.venv"'
Start-Process -FilePath ($pythonCmd).Source -ArgumentList "-m venv ./scripts/.venv" -Wait -NoNewWindow

$venvPythonPath = "./scripts/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/bin/python"
}

Write-Host "Running manageacl.py. Arguments to script: $scriptArgs"
Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/manageacl.py --search-service $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX $scriptArgs" -Wait -NoNewWindow
