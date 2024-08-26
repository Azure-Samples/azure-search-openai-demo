## Set the preference to stop on the first error
$ErrorActionPreference = "Stop"

& $PSScriptRoot\loadenv.ps1

$venvPythonPath = "./scripts/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/bin/python"
}

if ([string]::IsNullOrEmpty($env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT)) {
    Write-Error "AZURE_ADLS_GEN2_STORAGE_ACCOUNT must be set in order to continue"
    exit 1
}

Write-Host 'Running "adlsgen2setup.py"'
$cwd = (Get-Location)
Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/adlsgen2setup.py `"$cwd/data`" --data-access-control ./scripts/sampleacls.json --storage-account $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT -v" -Wait -NoNewWindow
