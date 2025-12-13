$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  # fallback to python3 if python not found
  $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Error "Python not found. Please install Python and ensure it's in your PATH."
    exit 1
}

Write-Host 'Creating python virtual environment ".venv"'
$process = Start-Process -FilePath ($pythonCmd).Source -ArgumentList "-m venv ./.venv" -Wait -NoNewWindow -PassThru
if ($process.ExitCode -ne 0) {
    Write-Error "Failed to create virtual environment with exit code $($process.ExitCode)"
    exit $process.ExitCode
}

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

Write-Host 'Installing dependencies from "requirements.txt" into virtual environment'
$process = Start-Process -FilePath $venvPythonPath -ArgumentList "-m pip install -r app/backend/requirements.txt" -Wait -NoNewWindow -PassThru
if ($process.ExitCode -ne 0) {
    Write-Error "Failed to install dependencies with exit code $($process.ExitCode)"
    exit $process.ExitCode
}
