if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host 'Python not found on $PATH'
  exit -1
}

Write-Host ""
Write-Host "Loading azd .env file from current environment"
Write-Host ""

$output = azd env get-values

foreach ($line in $output) {
  $name, $value = $line.Split("=")
  $value = $value -replace '^\"|\"$'
  [Environment]::SetEnvironmentVariable($name, $value)
}

Write-Host "Environment variables set."

Write-Host 'Creating python virtual environment "scripts/.venv"'

python -m venv ./scripts/.venv
./scripts/.venv/scripts/pip3 install -r ./scripts/requirements.txt
./scripts/prepdocs.py '.\data\*' --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX -v