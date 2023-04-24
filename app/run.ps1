Set-Location frontend
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to restore frontend npm packages"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Building frontend"
Write-Host ""
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build frontend"
    exit $LASTEXITCODE
}

Set-Location ../backend
$venvPythonPath = "./backend_env/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./backend_env/bin/python"
}

Write-Host ""
Write-Host "Starting backend"
Write-Host ""
Start-Process http://127.0.0.1:5000

Start-Process -FilePath $venvPythonPath -ArgumentList "./app.py" -Wait -NoNewWindow

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start backend"
    exit $LASTEXITCODE
}