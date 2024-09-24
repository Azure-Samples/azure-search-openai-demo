Write-Host "Checking if authentication should be setup..."

$AZURE_USE_AUTHENTICATION = (azd env get-value AZURE_USE_AUTHENTICATION)
if ($AZURE_USE_AUTHENTICATION -ne "true") {
  Write-Host "AZURE_USE_AUTHENTICATION is not set, skipping authentication setup."
  Exit 0
}

. ./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/auth_init.py" -Wait -NoNewWindow
