$output = azd env get-values

foreach ($line in $output) {
  $name, $value = $line.Split("=")
  $value = $value -replace '^\"|\"$'
  [Environment]::SetEnvironmentVariable($name, $value)
}

Write-Host "Environment variables set."

python -m venv scripts/.venv
scripts/scripts/.venv/scripts/python pip install -r ./scripts/requirements.txt
scripts/scripts/.venv/scripts/python ./scripts/prepdocs.py '.\data\*' --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX -v