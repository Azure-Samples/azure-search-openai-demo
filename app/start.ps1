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


Write-Host 'Creating python virtual environment ".venv"'
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  # fallback to python3 if python not found
  $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
Start-Process -FilePath ($pythonCmd).Source -ArgumentList "-m venv .venv" -Wait -NoNewWindow

Write-Host ""
Write-Host "Restoring backend python packages"
Write-Host ""

$directory = Get-Location
$venvPythonPath = "$directory/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "$directory/.venv/bin/python"
}

Start-Process -FilePath $venvPythonPath -ArgumentList "-m pip install -r backend/requirements.txt" -Wait -NoNewWindow
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to restore backend python packages"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Restoring frontend npm packages"
Write-Host ""
Set-Location ./frontend
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

$port = 50505
$hostname = "localhost"
Start-Process -FilePath $venvPythonPath -ArgumentList "-m quart --app main:app run --port $port --host $hostname --reload" -Wait -NoNewWindow

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start backend"
    exit $LASTEXITCODE
}
