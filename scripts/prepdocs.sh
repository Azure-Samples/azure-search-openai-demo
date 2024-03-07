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

keyVaultName=""
if [ -n "$AZURE_KEY_VAULT_NAME" ]; then
  keyVaultName="--keyvaultname $AZURE_KEY_VAULT_NAME"
fi

visionSecretNameArg=""
if [ -n "$VISION_SECRET_NAME" ]; then
  visionSecretNameArg="--visionsecretname $VISION_SECRET_NAME"
fi

searchSecretNameArg=""
if [ -n "$AZURE_SEARCH_SECRET_NAME" ]; then
  searchSecretNameArg="--searchsecretname $AZURE_SEARCH_SECRET_NAME"
fi

if [ "$USE_GPT4V" = true ]; then
  searchImagesArg="--searchimages"
fi

if [ "$USE_VECTORS" = false ]; then
  disableVectorsArg="--novectors"
fi

if [ "$USE_LOCAL_PDF_PARSER" = true ]; then
  localPdfParserArg="--localpdfparser"
fi

if [ "$USE_LOCAL_HTML_PARSER" = true ]; then
  localHtmlParserArg="--localhtmlparser"
fi

if [ -n "$AZURE_TENANT_ID" ]; then
  tenantArg="--tenantid $AZURE_TENANT_ID"
fi

if [ -n "$USE_FEATURE_INT_VECTORIZATION" ]; then
  integratedVectorizationArg="--useintvectorization $USE_FEATURE_INT_VECTORIZATION"
fi

./scripts/.venv/bin/python ./scripts/prepdocs.py './data/*' --verbose \
--subscriptionid $AZURE_SUBSCRIPTION_ID  \
--storageaccount "$AZURE_STORAGE_ACCOUNT" --container "$AZURE_STORAGE_CONTAINER" --storageresourcegroup $AZURE_STORAGE_RESOURCE_GROUP \
--searchservice "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" \
$searchAnalyzerNameArg $searchSecretNameArg \
--openaihost "$OPENAI_HOST" --openaimodelname "$AZURE_OPENAI_EMB_MODEL_NAME" \
--openaiservice "$AZURE_OPENAI_SERVICE" --openaideployment "$AZURE_OPENAI_EMB_DEPLOYMENT"  \
--openaikey "$OPENAI_API_KEY" --openaiorg "$OPENAI_ORGANIZATION" \
--documentintelligenceservice "$AZURE_DOCUMENTINTELLIGENCE_SERVICE" \
$searchImagesArg $visionEndpointArg $visionKeyArg $visionSecretNameArg \
$adlsGen2StorageAccountArg $adlsGen2FilesystemArg $adlsGen2FilesystemPathArg \
$tenantArg $aclArg \
$disableVectorsArg $localPdfParserArg $localHtmlParserArg \
$keyVaultName \
$integratedVectorizationArg
