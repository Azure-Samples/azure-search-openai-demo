## Deploying with minimal costs

* Azure App Service: Free tier

* Azure OpenAI: Use local server locally. Turn off vectors so that no embedding models are needed.

* Azure AI Document Intelligence: Use free SKU (with 2-page documents) or local PDF parser

* Azure AI search: free sku, no semantic search, we need to use keys!

* Azure Monitor: Disable

* Blob storage: No free tier, could disable storage?

azd env set AZURE_APP_SERVICE_SKU F1
azd env set AZURE_SEARCH_SERVICE_SKU free
azd env set AZURE_USE_APPLICATION_INSIGHTS false
azd env set AZURE_FORMRECOGNIZER_SKU free

app service - limit per region - centralus X


ServiceQuotaExceeded: Operation would exceed 'free' tier service quota. You are using 1 out of 1 'free' tier service quota. If you need more quota, please submit a quota increase request with issue type 'Service and subscription limits (quota)' and quota type 'Search' following https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-manager-quota-errors.
