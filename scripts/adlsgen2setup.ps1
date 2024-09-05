## Set the preference to stop on the first error
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
& $PSScriptRoot\loadenv.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

if ([string]::IsNullOrEmpty($env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT)) {
    Write-Error "AZURE_ADLS_GEN2_STORAGE_ACCOUNT must be set in order to continue"
    exit 1
}

Write-Host 'Running "adlsgen2setup.py"'
Start-Process -FilePath $venvPythonPath -ArgumentList "$projectRoot/scripts/adlsgen2setup.py `"$projectRoot/data`" --data-access-control $projectRoot/scripts/sampleacls.json --storage-account $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT -v" -Wait -NoNewWindow
