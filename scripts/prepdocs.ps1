$output = azd env get-values

foreach ($line in $output) {
  $name, $value = $line.Split("=")
  $value = $value -replace '^\"|\"$'
  [Environment]::SetEnvironmentVariable($name, $value)
}

Write-Host "Environment variables set."

pip install -r ./scripts/requirements.txt --quiet
# Add if having Azure authentication issues: --searchkey $env:AZURE_SEARCH_KEY  --storagekey $env:AZURE_STORAGE_KEY
python ./scripts/prepdocs.py './data/*' --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX -v
