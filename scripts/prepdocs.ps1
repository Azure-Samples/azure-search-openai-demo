Write-Host ""
Write-Host "Loading azd .env file from current environment"
Write-Host ""

$output = azd env get-values

foreach ($line in $output) {
  if (!$line.Contains('=')) {
    continue
  }

  $name, $value = $line.Split("=")
  $value = $value -replace '^\"|\"$'
  [Environment]::SetEnvironmentVariable($name, $value)
}

Write-Host "Environment variables set."

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  # fallback to python3 if python not found
  $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

Write-Host 'Creating python virtual environment "scripts/.venv"'
Start-Process -FilePath ($pythonCmd).Source -ArgumentList "-m venv ./scripts/.venv" -Wait -NoNewWindow

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
  Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/prepdocs.py --datalakestorageaccount $env:ADLS_GEN2_STORAGE_ACCOUNT $adlsGen2FilesystemArg $adlsGen2FilesystemPathArg --useacls --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME --openaihost $env:OPENAI_HOST --openaiorg $env:OPENAI_ORGANIZATION --openaiservice $env:AZURE_OPENAI_SERVICE --openaideployment $env:AZURE_OPENAI_EMB_DEPLOYMENT --index $env:AZURE_SEARCH_INDEX --formrecognizerservice $env:AZURE_FORMRECOGNIZER_SERVICE --tenantid $env:AZURE_TENANT_ID --openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME -v" -Wait -NoNewWindow
} else {
  Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/prepdocs.py `"$cwd/data/*`" --storageaccount $env:AZURE_STORAGE_ACCOUNT --container $env:AZURE_STORAGE_CONTAINER --searchservice $env:AZURE_SEARCH_SERVICE --openaihost $env:OPENAI_HOST --openaiorg $env:OPENAI_ORGANIZATION --openaiservice $env:AZURE_OPENAI_SERVICE --openaideployment $env:AZURE_OPENAI_EMB_DEPLOYMENT --openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME --index $env:AZURE_SEARCH_INDEX --formrecognizerservice $env:AZURE_FORMRECOGNIZER_SERVICE --tenantid $env:AZURE_TENANT_ID --openaimodelname $env:AZURE_OPENAI_EMB_MODEL_NAME -v" -Wait -NoNewWindow
}
