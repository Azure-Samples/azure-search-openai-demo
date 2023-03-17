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

Write-Host 'Installing dependencies from "requirements.txt" into virtual environment'
./scripts/.venv/scripts/python -m pip install -r ./scripts/requirements.txt

Write-Host 'Running "prepdocs.py"'
./scripts/.venv/scripts/python ./scripts/prepdocs.py '.\data\*' --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX --tenantid $env:AZURE_TENANT_ID -v