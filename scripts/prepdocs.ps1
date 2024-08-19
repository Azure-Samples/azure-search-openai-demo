./scripts/loadenv.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

Write-Host 'Running "prepdocs.py"'

# if AZURE_PUBLIC_NETWORK_ACCESS env variable exists and is Disabled, exit immediately
if ($env:AZURE_PUBLIC_NETWORK_ACCESS -eq "Disabled") {
  Write-Host "AZURE_PUBLIC_NETWORK_ACCESS is set to Disabled. Exiting."
  exit 0
}

# Optional Data Lake Storage Gen2 args if using sample data for login and access control
if ($env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT) {
  $adlsGen2StorageAccountArg = "--datalakestorageaccount $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT"
  $adlsGen2FilesystemPathArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM_PATH) {
    $adlsGen2FilesystemPathArg = "--datalakepath $env:AZURE_ADLS_GEN2_FILESYSTEM_PATH"
  }
  $adlsGen2FilesystemArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM) {
    $adlsGen2FilesystemArg = "--datalakefilesystem $env:AZURE_ADLS_GEN2_FILESYSTEM"
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

if ($env:USE_GPT4V -eq $true) {
  $searchImagesArg = "--searchimages"
}

if ($env:USE_VECTORS -eq $false) {
  $disableVectorsArg="--novectors"
}

if ($env:AZURE_OPENAI_EMB_DIMENSIONS) {
  $openaiDimensionsArg = "--openaidimensions $env:AZURE_OPENAI_EMB_DIMENSIONS"
}

if ($env:USE_LOCAL_PDF_PARSER -eq $true) {
  $localPdfParserArg = "--localpdfparser"
}

if ($env:USE_LOCAL_HTML_PARSER -eq $true) {
  $localHtmlParserArg = "--localhtmlparser"
}

if ($env:AZURE_TENANT_ID) {
  $tenantArg = "--tenantid $env:AZURE_TENANT_ID"
}

if ($env:USE_FEATURE_INT_VECTORIZATION) {
  $integratedVectorizationArg = "--useintvectorization $env:USE_FEATURE_INT_VECTORIZATION"
}

if ($env:AZURE_OPENAI_API_KEY_OVERRIDE) {
  $openaiApiKeyArg = "--openaikey $env:AZURE_OPENAI_API_KEY_OVERRIDE"
} elseif ($env:OPENAI_API_KEY) {
  $openaiApiKeyArg = "--openaikey $env:OPENAI_API_KEY"
}

$cwd = (Get-Location)
$dataArg = "`"$cwd/data/*`""
$additionalArgs = ""
if ($args) {
  $additionalArgs = "$args"
}

$argumentList = "./app/backend/prepdocs.py $dataArg --verbose " + `
"--subscriptionid $env:AZURE_SUBSCRIPTION_ID " + `
"--storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --storageresourcegroup $env:AZURE_STORAGE_RESOURCE_GROUP " + `
"--searchservice $env:AZURE_SEARCH_SERVICE --index $env:AZURE_SEARCH_INDEX " + `
"$searchAnalyzerNameArg " + `
"--openaihost `"$env:OPENAI_HOST`" --openaimodelname `"$env:AZURE_OPENAI_EMB_MODEL_NAME`" $openaiDimensionsArg " + `
"--openaiservice `"$env:AZURE_OPENAI_SERVICE`" --openaideployment `"$env:AZURE_OPENAI_EMB_DEPLOYMENT`" " + `
"--openaicustomurl `"$env:AZURE_OPENAI_CUSTOM_URL`" " + `
"$openaiApiKeyArg --openaiorg `"$env:OPENAI_ORGANIZATION`" " + `
"--documentintelligenceservice $env:AZURE_DOCUMENTINTELLIGENCE_SERVICE " + `
"$searchImagesArg $visionEndpointArg " + `
"$adlsGen2StorageAccountArg $adlsGen2FilesystemArg $adlsGen2FilesystemPathArg  " + `
"$tenantArg $aclArg " + `
"$disableVectorsArg $localPdfParserArg $localHtmlParserArg " + `
"$integratedVectorizationArg " + `
"$additionalArgs "

$argumentList

Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow
