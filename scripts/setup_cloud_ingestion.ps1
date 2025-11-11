$USE_CLOUD_INGESTION = (azd env get-value USE_CLOUD_INGESTION)
if ($USE_CLOUD_INGESTION -ne "true") {
  Exit 0
}

. ./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

Start-Process -FilePath $venvPythonPath -ArgumentList "./app/backend/setup_cloud_ingestion.py" -Wait -NoNewWindow
