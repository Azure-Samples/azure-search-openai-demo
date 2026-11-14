$USE_CLOUD_INGESTION_SHAREPOINT = (azd env get-value USE_CLOUD_INGESTION_SHAREPOINT 2>$null)
if ($USE_CLOUD_INGESTION_SHAREPOINT -ne "true") {
  Write-Host "USE_CLOUD_INGESTION_SHAREPOINT is not set, skipping SharePoint indexer app setup."
  Exit 0
}

. ./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

$process = Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/sharepoint_indexer_init.py" -Wait -NoNewWindow -PassThru
exit $process.ExitCode
