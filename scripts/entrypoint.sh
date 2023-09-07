python3 prepdocs.py --novectors --localpdfparser --verbose \
    --bloburl "$BLOB_URL" \
    --logfilename "$LOG_FILE_NAME" \
    --storageaccount "$AZURE_STORAGE_ACCOUNT" --container "$AZURE_STORAGE_CONTAINER" \
    --searchservice "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" \
    --openaiservice "$AZURE_OPENAI_SERVICE" --openaideployment "$AZURE_OPENAI_EMB_DEPLOYMENT" \
    --formrecognizerservice "$AZURE_FORMRECOGNIZER_SERVICE"
