# set all the environment variables
set +a
source <(azd env get-values)
set -a

az acr build -t prepdocs:1.0 -r $AZURE_CONTAINER_REGISTRY_NAME .

az containerapp job create \
    --name "job-prepdocs" --resource-group "$AZURE_RESOURCE_GROUP"  --environment $AZURE_CONTAINER_ENVIRONMENT_NAME \
    --trigger-type "Manual" \
    --replica-timeout 1800 --replica-retry-limit 0 --replica-completion-count 1 --parallelism 1 \
    --image $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/prepdocs:1.0 \
    --cpu "2" --memory "4Gi" \
    --env-vars "AZURE_ENV_NAME=$AZURE_ENV_NAME" \
        "AZURE_FORMRECOGNIZER_RESOURCE_GROUP=$AZURE_FORMRECOGNIZER_RESOURCE_GROUP" \
        "AZURE_FORMRECOGNIZER_SERVICE=$AZURE_FORMRECOGNIZER_SERVICE" \
        "AZURE_LOCATION=$AZURE_LOCATION" \
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT=$AZURE_OPENAI_CHATGPT_DEPLOYMENT" \
        "AZURE_OPENAI_CHATGPT_MODEL=$AZURE_OPENAI_CHATGPT_MODEL" \
        "AZURE_OPENAI_EMB_DEPLOYMENT=$AZURE_OPENAI_EMB_DEPLOYMENT" \
        "AZURE_OPENAI_RESOURCE_GROUP=$AZURE_OPENAI_RESOURCE_GROUP" \
        "AZURE_OPENAI_SERVICE=$AZURE_OPENAI_SERVICE" \
        "AZURE_RESOURCE_GROUP=$AZURE_RESOURCE_GROUP" \
        "AZURE_SEARCH_INDEX=$AZURE_SEARCH_INDEX" \
        "AZURE_SEARCH_SERVICE=$AZURE_SEARCH_SERVICE" \
        "AZURE_SEARCH_SERVICE_RESOURCE_GROUP=$AZURE_SEARCH_SERVICE_RESOURCE_GROUP" \
        "AZURE_STORAGE_ACCOUNT=$AZURE_STORAGE_ACCOUNT" \
        "AZURE_STORAGE_CONTAINER=$AZURE_STORAGE_CONTAINER" \
        "AZURE_STORAGE_RESOURCE_GROUP=$AZURE_STORAGE_RESOURCE_GROUP" \
        "AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID" \
        "AZURE_TENANT_ID=$AZURE_TENANT_ID" \
        "AZURE_USE_APPLICATION_INSIGHTS=$AZURE_USE_APPLICATION_INSIGHTS" \
        "BACKEND_URI=$BACKEND_URI" \
        "LOG_FILE_NAME=$(date +%Y-%m-%d_%H-%M-%S).log" \
        "BLOB_URL=https://jobsdemo.blob.core.windows.net/public/azure-container-apps.pdf" \
    --registry-server $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io \
    --registry-identity system \
    --mi-system-assigned

# give the job permissions to resources
# az role assignment create --role "Contributor" --assignee `az containerapp job show -n job-prepdocs -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
az role assignment create --role "Storage Blob Data Contributor" --assignee `az containerapp job show -n job-prepdocs -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
az role assignment create --role "Cognitive Services OpenAI User" --assignee `az containerapp job show -n job-prepdocs -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
az role assignment create --role "Cognitive Services User" --assignee `az containerapp job show -n job-prepdocs -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
az role assignment create --role "Search Index Data Contributor" --assignee `az containerapp job show -n job-prepdocs -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
az role assignment create --role "Search Service Contributor" --assignee `az containerapp job show -n job-prepdocs -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
az role assignment create --role "Storage Blob Data Contributor" --assignee `az containerapp job show -n job-prepdocs -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP

az containerapp job start \
    --name "job-prepdocs" --resource-group "$AZURE_RESOURCE_GROUP"
