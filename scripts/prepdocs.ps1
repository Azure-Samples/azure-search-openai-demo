./scripts/loadenv.ps1

$venvPythonPath = "./scripts/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/bin/python"
}

Write-Host 'Running "prepdocs.py"'
$cwd = (Get-Location)

# Optional Data Lake Storage Gen2 args if using sample data for login and access control
if ($env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT) {
  $adlsGen2StorageAccountArg = "--datalakestorageaccount $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT"
  $adlsGen2FilesystemPathArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM_PATH) {
    $adlsGen2FilesystemPathArg = "--datalakefilesystempath $env:ADLS_GEN2_FILESYSTEM_PATH"
  }
  $adlsGen2FilesystemArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM) {
    $adlsGen2FilesystemArg = "--datalakefilesystem $env:ADLS_GEN2_FILESYSTEM"
  }
}
if ($env:AZURE_USE_AUTHENTICATION) {
    $aclArg = "--useacls"
}
# Optional Search Analyzer name if using a custom analyzer
if ($env:AZURE_SEARCH_ANALYZER_NAME) {
  $searchAnalyzerNameArg = "--searchanalyzername $env:AZURE_SEARCH_ANALYZER_NAME"
}
if ($env:AZURE_VISION_ENDPOINT) {
  $visionEndpointArg = "--visionendpoint $env:AZURE_VISION_ENDPOINT"
}
if ($env:AZURE_VISION_KEY) {
  $visionKeyArg = "--visionkey $env:AZURE_VISION_KEY"
}

# If vision keys are stored in keyvault provide the keyvault name and secret name
if ($env:AZURE_KEY_VAULT_NAME) {
  $visionKeyVaultName = "--visionKeyVaultName $env:AZURE_KEY_VAULT_NAME"
}
if ($env:VISION_SECRET_NAME) {
  $visionKeyVaultkey = "--visionKeyVaultkey $env:VISION_SECRET_NAME"
}

$dataArg = "`"$cwd/data/*`""
if ($env:USE_GPT4V -eq $true) {
  $searchImagesArg = "--searchimages"
}

if ($env:AZURE_TENANT_ID) {
  $tenantArg = "--tenantid $env:AZURE_TENANT_ID"
}

$argumentList = "./scripts/prepdocs.py $dataArg $adlsGen2StorageAccountArg $adlsGen2FilesystemArg $adlsGen2FilesystemPathArg $searchAnalyzerNameArg " + `
"$aclArg --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER " + `
"--searchservice $env:AZURE_SEARCH_SERVICE --openaihost `"$env:OPENAI_HOST`" " + `
"--openaiservice `"$env:AZURE_OPENAI_SERVICE`" --openaikey `"$env:OPENAI_API_KEY`" " + `
"--openaiorg `"$env:OPENAI_ORGANIZATION`" --openaideployment `"$env:AZURE_OPENAI_EMB_DEPLOYMENT`" " + `
"--openaimodelname `"$env:AZURE_OPENAI_EMB_MODEL_NAME`" --index $env:AZURE_SEARCH_INDEX " + `
"$searchImagesArg $visionEndpointArg $visionKeyArg $visionKeyVaultkey $visionKeyVaultName " + `
"--formrecognizerservice $env:AZURE_FORMRECOGNIZER_SERVICE $tenantArg -v"
Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow
