./scripts/loadenv.ps1

$venvPythonPath = "./scripts/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/bin/python"
}

Write-Host 'Installing dependencies from "requirements.txt" into virtual environment'
Start-Process -FilePath $venvPythonPath -ArgumentList "-m pip install -r ./scripts/requirements.txt" -Wait -NoNewWindow



Write-Host 'Running "prepdocs.py"'
$cwd = (Get-Location)

if ($env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT) {
  $adlsGen2FilesystemPathArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM_PATH) {
    $adlsGen2FilesystemPathArg = "--datalakefilesystempath $env:ADLS_GEN2_FILESYSTEM_PATH"
  }
  $adlsGen2FilesystemArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM) {
    $adlsGen2FilesystemArg = "--datalakefilesystem $env:ADLS_GEN2_FILESYSTEM"
  }
} else {
  Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/prepdocs.py  --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --openaihost $env:OPENAI_HOST --openaiservice $env:AZURE_OPENAI_SERVICE --openaikey `"$env:OPENAI_API_KEY`" --openaiorg `"$env:OPENAI_ORGANIZATION`" --openaideployment $env:AZURE_OPENAI_EMB_DEPLOYMENT --openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME --index $env:AZURE_SEARCH_INDEX --formrecognizerservice $env:AZURE_FORMRECOGNIZER_SERVICE --tenantid $env:AZURE_TENANT_ID -v" -Wait -NoNewWindow
}

# Optional Data Lake Storage Gen2 args if using sample data for login and access control
$fileArg = "`"$cwd/data/*`""
if ($env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT) {
  $fileArg = "--datalakestorageaccount $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT"
  $adlsGen2FilesystemPathArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM_PATH) {
    $adlsGen2FilesystemPathArg = "--datalakefilesystempath $env:ADLS_GEN2_FILESYSTEM_PATH"
  }
  $adlsGen2FilesystemArg = ""
  if ($env:AZURE_ADLS_GEN2_FILESYSTEM) {
    $adlsGen2FilesystemArg = "--datalakefilesystem $env:ADLS_GEN2_FILESYSTEM"
  }
  $aclArg = "--useacls"
}
$argumentList = "./scripts/prepdocs.py $fileArg $adlsGen2FilesystemArg $adlsGen2FilesystemPathArg " + `
"$aclArg --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER " + `
"--searchservice $env:AZURE_SEARCH_SERVICE --openaihost $env:OPENAI_HOST " + `
"--openaiservice $env:AZURE_OPENAI_SERVICE --openaikey `"$env:OPENAI_API_KEY`" " + `
"--openaiorg `"$env:OPENAI_ORGANIZATION`" --openaideployment $env:AZURE_OPENAI_EMB_DEPLOYMENT " + `
"--openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME --index $env:AZURE_SEARCH_INDEX " + `
"--formrecognizerservice $env:AZURE_FORMRECOGNIZER_SERVICE --tenantid $env:AZURE_TENANT_ID -v"
Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow
