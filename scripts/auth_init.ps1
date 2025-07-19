Write-Host "Checking if authentication should be setup..."

$AZURE_USE_AUTHENTICATION = (azd env get-value AZURE_USE_AUTHENTICATION)
$AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS = (azd env get-value AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS)
$AZURE_ENFORCE_ACCESS_CONTROL = (azd env get-value AZURE_ENFORCE_ACCESS_CONTROL)
$USE_CHAT_HISTORY_COSMOS = (azd env get-value USE_CHAT_HISTORY_COSMOS)

if ($AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS -eq "true") {
  if ($AZURE_ENFORCE_ACCESS_CONTROL -ne "true") {
    Write-Host "AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS is set to true, but AZURE_ENFORCE_ACCESS_CONTROL is not set to true. Please set it and retry."
    Exit 1
  }
}

if ($USE_CHAT_HISTORY_COSMOS -eq "true") {
  if ($AZURE_USE_AUTHENTICATION -ne "true") {
    Write-Host "AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS, AZURE_ENFORCE_ACCESS_CONTROL, or USE_CHAT_HISTORY_COSMOS is set to true, but AZURE_USE_AUTHENTICATION is not set to true. Please set and retry."
    Exit 1
  }
}

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
