$AZURE_USE_PRIVATE_ENDPOINT = (azd env get-value AZURE_USE_PRIVATE_ENDPOINT 2>$null)
if ($AZURE_USE_PRIVATE_ENDPOINT -ne "true") {
  Exit 0
}

. ./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

$process = Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/approve_search_private_links.py" -Wait -NoNewWindow -PassThru
exit $process.ExitCode
