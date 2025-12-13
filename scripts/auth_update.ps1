$AZURE_USE_AUTHENTICATION = (azd env get-value AZURE_USE_AUTHENTICATION)
if ($AZURE_USE_AUTHENTICATION -ne "true") {
  Exit 0
}

. ./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

$process = Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/auth_update.py" -Wait -NoNewWindow -PassThru
if ($process.ExitCode -ne 0) {
    Write-Error "auth_update.py failed with exit code $($process.ExitCode)"
    exit $process.ExitCode
}
