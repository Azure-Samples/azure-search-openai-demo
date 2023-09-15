## Set the preference to stop on the first error
$ErrorActionPreference = "Stop"

. ./scripts/loadenv.ps1

$venvPythonPath = "./scripts/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/bin/python"
}

Write-Host "Running manageacl.py. Arguments to script: $scriptArgs"
Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/manageacl.py --search-service $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX $scriptArgs" -Wait -NoNewWindow
