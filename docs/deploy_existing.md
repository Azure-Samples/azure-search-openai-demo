
# RAG chat: Deploying with existing Azure resources

If you already have existing Azure resources, or if you want to specify the exact name of new Azure Resource, you can do so by setting `azd` environment values.
You should set these values before running `azd up`. Once you've set them, return to the [deployment steps](../README.md#deploying).

* [Resource group](#resource-group)
* [OpenAI resource](#openai-resource)
* [Azure AI Search resource](#azure-ai-search-resource)
* [Azure App Service Plan and App Service resources](#azure-app-service-plan-and-app-service-resources)
* [Azure AI Vision resources](#azure-ai-vision-resources)
* [Azure Document Intelligence resource](#azure-document-intelligence-resource)
* [Azure Speech resource](#azure-speech-resource)
* [Azure Storage Account](#azure-storage-account)

> [!NOTE]
> When you specify an existing resource, the Bicep templates will still attempt to re-provision or update the service. This means some service parameters may be overridden with the default values from the templates. If you need to preserve specific configurations, review the Bicep files in `infra/` and adjust the parameters accordingly.
>
> **RBAC considerations**: This project uses managed identity and RBAC role assignments for authentication between services. If your existing resources are in a different resource group than the main deployment, the RBAC role assignments may not be created correctly, and you may need to manually assign the required roles. For the simplest setup, we recommend keeping all resources in the same resource group.

## Resource group

1. Run `azd env set AZURE_RESOURCE_GROUP {Name of existing resource group}`
1. Run `azd env set AZURE_LOCATION {Location of existing resource group}`

## OpenAI resource

### Azure OpenAI

1. Run `azd env set AZURE_OPENAI_SERVICE {Name of existing OpenAI service}`
1. Run `azd env set AZURE_OPENAI_RESOURCE_GROUP {Name of existing resource group that OpenAI service is provisioned to}`
1. Run `azd env set AZURE_OPENAI_LOCATION {Location of existing OpenAI service}`
1. Run `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT {Name of existing chat deployment}`. Only needed if your chat deployment name is not the default 'gpt-4.1-mini'.
1. Run `azd env set AZURE_OPENAI_CHATGPT_MODEL {Model name of existing chat deployment}`. Only needed if your chat model is not the default 'gpt-4.1-mini'.
1. Run `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION {Version string for existing chat deployment}`. Only needed if your chat deployment model version is not the default '2024-07-18'. You definitely need to change this if you changed the model.
1. Run `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_SKU {Name of SKU for existing chat deployment}`. Only needed if your chat deployment SKU is not the default 'Standard', like if it is 'GlobalStandard' instead.
1. Run `azd env set AZURE_OPENAI_EMB_DEPLOYMENT {Name of existing embedding deployment}`. Only needed if your embeddings deployment is not the default 'embedding'.
1. Run `azd env set AZURE_OPENAI_EMB_MODEL_NAME {Model name of existing embedding deployment}`. Only needed if your embeddings model is not the default 'text-embedding-3-large'.
1. Run `azd env set AZURE_OPENAI_EMB_DIMENSIONS {Dimensions for existing embedding deployment}`. Only needed if your embeddings model is not the default 'text-embedding-3-large'.
1. Run `azd env set AZURE_OPENAI_EMB_DEPLOYMENT_VERSION {Version string for existing embedding deployment}`. If your embeddings deployment is one of the 'text-embedding-3' models, set this to the number 1.
1. This project does *not* use keys when authenticating to Azure OpenAI. However, if your Azure OpenAI service must have key access enabled for some reason (like for use by other projects), then run `azd env set AZURE_OPENAI_DISABLE_KEYS false`. The default value is `true` so you should only run the command if you need key access.

When you run `azd up` after and are prompted to select a value for `openAiResourceGroupLocation`, make sure to select the same location as the existing OpenAI resource group.

> [!WARNING]
> If using a different resource group, the following RBAC roles may not be assigned correctly: `Cognitive Services OpenAI User` for the backend and search service. You may need to manually assign these roles.

### Openai.com OpenAI

1. Run `azd env set OPENAI_HOST openai`
2. Run `azd env set OPENAI_ORGANIZATION {Your OpenAI organization}`
3. Run `azd env set OPENAI_API_KEY {Your OpenAI API key}`
4. Run `azd up`

You can retrieve your OpenAI key by checking [your user page](https://platform.openai.com/account/api-keys) and your organization by navigating to [your organization page](https://platform.openai.com/account/org-settings).
Learn more about creating an OpenAI free trial at [this link](https://openai.com/pricing).
Do *not* check your key into source control.

When you run `azd up` after and are prompted to select a value for `openAiResourceGroupLocation`, you can select any location as it will not be used.

## Azure AI Search resource

1. Run `azd env set AZURE_SEARCH_SERVICE {Name of existing Azure AI Search service}`
1. Run `azd env set AZURE_SEARCH_SERVICE_RESOURCE_GROUP {Name of existing resource group with ACS service}`
1. If that resource group is in a different location than the one you'll pick for the `azd up` step,
  then run `azd env set AZURE_SEARCH_SERVICE_LOCATION {Location of existing service}`
1. If the search service's SKU is not standard, then run `azd env set AZURE_SEARCH_SERVICE_SKU {Name of SKU}`. If you specify the free tier, then your app will no longer be able to use semantic ranker. You can [switch between Basic, S1, S2, and S3 tiers](https://learn.microsoft.com/azure/search/search-capacity-planning#change-your-pricing-tier), but you can't switch to or from Free, S3HD, L1, or L2. ([See other possible SKU values](https://learn.microsoft.com/azure/templates/microsoft.search/searchservices?pivots=deployment-language-bicep#sku))
1. If you have an existing index that is set up with all the expected fields, then run `azd env set AZURE_SEARCH_INDEX {Name of existing index}`. Otherwise, the `azd up` command will create a new index.

You can also customize the search service (new or existing) for non-English searches:

1. To configure the language of the search query to a value other than "en-US", run `azd env set AZURE_SEARCH_QUERY_LANGUAGE {Name of query language}`. ([See other possible values](https://learn.microsoft.com/rest/api/searchservice/preview-api/search-documents#queryLanguage))
1. To turn off the spell checker, run `azd env set AZURE_SEARCH_QUERY_SPELLER none`. Consult [this table](https://learn.microsoft.com/rest/api/searchservice/preview-api/search-documents#queryLanguage) to determine if spell checker is supported for your query language.
1. To configure the name of the analyzer to use for a searchable text field to a value other than "en.microsoft", run `azd env set AZURE_SEARCH_ANALYZER_NAME {Name of analyzer name}`. ([See other possible values](https://learn.microsoft.com/dotnet/api/microsoft.azure.search.models.field.analyzer?view=azure-dotnet-legacy&viewFallbackFrom=azure-dotnet))

> [!WARNING]
> If using a different resource group, the following RBAC roles may not be assigned correctly and may need to be manually assigned:
>
> * Backend identity: `Search Index Data Reader`, `Search Index Data Contributor`
> * Signed-in user (`principalId`): `Search Index Data Reader`, `Search Index Data Contributor`, `Search Service Contributor`

## Azure App Service Plan and App Service resources

1. Run `azd env set AZURE_APP_SERVICE_PLAN {Name of existing Azure App Service Plan}`
1. Run `azd env set AZURE_APP_SERVICE {Name of existing Azure App Service}`.
1. Run `azd env set AZURE_APP_SERVICE_SKU {SKU of Azure App Service, defaults to B1}`.

## Azure AI Vision resources

1. Run `azd env set AZURE_VISION_SERVICE {Name of existing Azure AI Vision Service Name}`
1. Run `azd env set AZURE_VISION_RESOURCE_GROUP {Name of existing Azure AI Vision Resource Group Name}`
1. Run `azd env set AZURE_VISION_LOCATION {Name of existing Azure AI Vision Location}`
1. Run `azd env set AZURE_VISION_SKU {SKU of Azure AI Vision service, defaults to F0}`

> [!WARNING]
> If using a different resource group, the following RBAC roles may not be assigned correctly: `Cognitive Services User` for the backend and search service. You may need to manually assign these roles.

## Azure Document Intelligence resource

In order to support analysis of many document formats, this repository uses a preview version of Azure Document Intelligence (formerly Form Recognizer) that is only available in [limited regions](https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-layout).
If your existing resource is in one of those regions, then you can re-use it by setting the following environment variables:

1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_SERVICE {Name of existing Azure AI Document Intelligence service}`
1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_LOCATION {Location of existing service}`
1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_RESOURCE_GROUP {Name of resource group with existing service, defaults to main resource group}`
1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_SKU {SKU of existing service, defaults to S0}`

> [!WARNING]
> If using a different resource group, the following RBAC roles may not be assigned correctly: `Cognitive Services User` for the backend (required for user upload feature). You may need to manually assign these roles.

## Azure Speech resource

1. Run `azd env set AZURE_SPEECH_SERVICE {Name of existing Azure Speech service}`
1. Run `azd env set AZURE_SPEECH_SERVICE_RESOURCE_GROUP {Name of existing resource group with speech service}`
1. If that resource group is in a different location than the one you'll pick for the `azd up` step,
  then run `azd env set AZURE_SPEECH_SERVICE_LOCATION {Location of existing service}`
1. If the speech service's SKU is not "S0", then run `azd env set AZURE_SPEECH_SERVICE_SKU {Name of SKU}`.

> [!WARNING]
> If using a different resource group, the following RBAC roles may not be assigned correctly: `Cognitive Services Speech User` for the backend and user. You may need to manually assign these roles.

## Azure Storage Account

1. Run `azd env set AZURE_STORAGE_ACCOUNT {Name of existing Azure Storage Account}`
1. Run `azd env set AZURE_STORAGE_RESOURCE_GROUP {Name of existing resource group with storage account}`
1. If that resource group is in a different location than the one you'll pick for the `azd up` step,
  then run `azd env set AZURE_STORAGE_ACCOUNT_LOCATION {Location of existing storage account}`
1. To change the storage SKU from the default `Standard_LRS`, run `azd env set AZURE_STORAGE_SKU {Name of SKU}`. For production, we recommend `Standard_ZRS` for improved resiliency.

> [!WARNING]
> If using a different resource group, the following RBAC roles may not be assigned correctly: `Storage Blob Data Reader`, `Storage Blob Data Contributor`, and `Storage Blob Data Owner` for the backend, user, and search service. You may need to manually assign these roles.
