 #!/bin/sh

. ./scripts/loadenv.sh

echo 'Running "prepdocs.py"'

if [ -n "$AZURE_ADLS_GEN2_STORAGE_ACCOUNT" ]; then
  adlsGen2StorageAccountArg="--datalakestorageaccount $AZURE_ADLS_GEN2_STORAGE_ACCOUNT"
  adlsGen2FilesystemPathArg=""
  if [ -n "$AZURE_ADLS_GEN2_FILESYSTEM_PATH" ]; then
    adlsGen2FilesystemPathArg="--datalakefilesystempath $AZURE_ADLS_GEN2_FILESYSTEM_PATH"
  fi
  adlsGen2FilesystemArg=""
  if [ -n "$AZURE_ADLS_GEN2_FILESYSTEM" ]; then
    adlsGen2FilesystemArg="--datalakefilesystem $AZURE_ADLS_GEN2_FILESYSTEM"
  fi
  aclArg="--useacls"
fi

if [ -n "$AZURE_SEARCH_ANALYZER_NAME" ]; then
  searchAnalyzerNameArg="--searchanalyzername $AZURE_SEARCH_ANALYZER_NAME"
fi

if [ -n "$AZURE_USE_AUTHENTICATION" ]; then
  aclArg="--useacls"
fi

visionEndpointArg=""
if [ -n "$AZURE_VISION_ENDPOINT" ]; then
  visionEndpointArg="--visionendpoint $AZURE_VISION_ENDPOINT"
fi

visionKeyArg=""
if [ -n "$AZURE_VISION_KEY" ]; then
  visionKeyArg="--visionkey $AZURE_VISION_KEY"
fi

visionKeyVaultName=""
if [ -n "$AZURE_KEY_VAULT_NAME" ]; then
  visionKeyVaultName="--visionKeyVaultName $AZURE_KEY_VAULT_NAME"
fi

visionKeyVaultkey=""
if [ -n "$VISION_SECRET_NAME" ]; then
  visionKeyVaultkey="--visionKeyVaultkey $VISION_SECRET_NAME"
fi

if [ "$USE_GPT4V" = true ]; then
  searchImagesArg="--searchimages"
fi

if [ -n "$AZURE_TENANT_ID" ]; then
  tenantArg="--tenantid $AZURE_TENANT_ID"
fi

./scripts/.venv/bin/python ./scripts/prepdocs.py \
'./data/*' $adlsGen2StorageAccountArg $adlsGen2FilesystemArg $adlsGen2FilesystemPathArg $searchAnalyzerNameArg \
$aclArg  --storageaccount "$AZURE_STORAGE_ACCOUNT" \
$searchImagesArg $visionEndpointArg $visionKeyArg $visionKeyVaultkey $visionKeyVaultName \
--container "$AZURE_STORAGE_CONTAINER" --searchservice "$AZURE_SEARCH_SERVICE" \
--openaiservice "$AZURE_OPENAI_SERVICE" --openaideployment "$AZURE_OPENAI_EMB_DEPLOYMENT" \
--openaimodelname "$AZURE_OPENAI_EMB_MODEL_NAME" --index "$AZURE_SEARCH_INDEX" \
--formrecognizerservice "$AZURE_FORMRECOGNIZER_SERVICE" --openaimodelname "$AZURE_OPENAI_EMB_MODEL_NAME" \
$tenantArg --openaihost "$OPENAI_HOST" \
--openaikey "$OPENAI_API_KEY" -v
