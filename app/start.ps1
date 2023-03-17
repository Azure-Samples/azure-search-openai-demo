Write-Host ""
Write-Host "Loading azd .env file from current environment"
Write-Host ""

foreach ($line in (& azd env get-values)) {
    if ($line -match "([^=]+)=(.*)") {
        $key = $matches[1]
        $value = $matches[2] -replace '^"|"$'
        Set-Item -Path "env:\$key" -Value $value
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to load environment variables from azd environment"
    exit $LASTEXITCODE
}


Write-Host 'Creating python virtual environment "backend/backend_env"'
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  # fallback to python3 if python not found
  $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
Start-Process -FilePath ($pythonCmd).Source -ArgumentList "-m venv ./backend/backend_env" -Wait -NoNewWindow

Write-Host ""
Write-Host "Restoring backend python packages"
Write-Host ""

$venvPath = "scripts"
if (-not (Test-Path -Path "./backend/backend_env/$venvPath")) {
  # fallback to Linux venv path
  $venvPath = "bin"
} 
$venvPythonPath = "./scripts/.venv/$venvPath/python.exe"
if (-not (Test-Path -Path $venvPythonPath)) {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/$venvPath/python"
} 

Set-Location backend
Start-Process -FilePath $venvPythonPath -ArgumentList "-m pip install -r requirements.txt" -Wait -NoNewWindow
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to restore backend python packages"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Restoring frontend npm packages"
Write-Host ""
Set-Location ../frontend
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

Write-Host ""
Write-Host "Starting backend"
Write-Host ""
Set-Location ../backend
Start-Process http://127.0.0.1:5000

Start-Process -FilePath $venvPythonPath -ArgumentList "./app.py" -Wait -NoNewWindow

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start backend"
    exit $LASTEXITCODE
}
