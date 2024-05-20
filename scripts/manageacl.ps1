## Set the preference to stop on the first error
$ErrorActionPreference = "Stop"

& $PSScriptRoot\loadenv.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

Write-Host "Running manageacl.py. Arguments to script: $args"
Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/manageacl.py --search-service $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX $args" -Wait -NoNewWindow
