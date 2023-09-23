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
  Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/prepdocs.py --datalakestorageaccount $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT $adlsGen2FilesystemArg $adlsGen2FilesystemPathArg --useacls --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --openaihost $env:OPENAI_HOST --openaiservice $env:AZURE_OPENAI_SERVICE --openaikey `"$env:OPENAI_API_KEY`" --openaiorg `"$env:OPENAI_ORGANIZATION`" --openaideployment $env:AZURE_OPENAI_EMB_DEPLOYMENT --openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME --index $env:AZURE_SEARCH_INDEX --formrecognizerservice $env:AZURE_FORMRECOGNIZER_SERVICE --tenantid $env:AZURE_TENANT_ID -v" -Wait -NoNewWindow
} else {
  Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/prepdocs.py `"$cwd/data/*`" --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --openaihost $env:OPENAI_HOST --openaiservice $env:AZURE_OPENAI_SERVICE --openaikey `"$env:OPENAI_API_KEY`" --openaiorg `"$env:OPENAI_ORGANIZATION`" --openaideployment $env:AZURE_OPENAI_EMB_DEPLOYMENT --openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME --index $env:AZURE_SEARCH_INDEX --formrecognizerservice $env:AZURE_FORMRECOGNIZER_SERVICE --tenantid $env:AZURE_TENANT_ID -v" -Wait -NoNewWindow
}
