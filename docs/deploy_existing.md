
# Deploying with existing Azure resources

If you already have existing Azure resources, you can re-use those by setting `azd` environment values.
You should set these values before running `azd up`. Once you've set them, return to the [deployment steps](../README.md#deploying).

* [Existing resource group](#existing-resource-group)
* [Existing OpenAI resource](#existing-openai-resource)
* [Existing Azure AI Search resource](#existing-azure-ai-search-resource)
* [Existing Azure Document Intelligence resource](#existing-azure-document-intelligence-resource)
* [Other existing Azure resources](#other-existing-azure-resources)

## Existing resource group

1. Run `azd env set AZURE_RESOURCE_GROUP {Name of existing resource group}`
1. Run `azd env set AZURE_LOCATION {Location of existing resource group}`

## Existing OpenAI resource

### Azure OpenAI:

1. Run `azd env set AZURE_OPENAI_SERVICE {Name of existing OpenAI service}`
1. Run `azd env set AZURE_OPENAI_RESOURCE_GROUP {Name of existing resource group that OpenAI service is provisioned to}`
1. Run `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT {Name of existing ChatGPT deployment}`. Only needed if your ChatGPT deployment is not the default 'chat'.
1. Run `azd env set AZURE_OPENAI_EMB_DEPLOYMENT {Name of existing GPT embedding deployment}`. Only needed if your embeddings deployment is not the default 'embedding'.

When you run `azd up` after and are prompted to select a value for `openAiResourceGroupLocation`, make sure to select the same location as the existing OpenAI resource group.

### Openai.com OpenAI:

1. Run `azd env set OPENAI_HOST openai`
2. Run `azd env set OPENAI_ORGANIZATION {Your OpenAI organization}`
3. Run `azd env set OPENAI_API_KEY {Your OpenAI API key}`
4. Run `azd up`

You can retrieve your OpenAI key by checking [your user page](https://platform.openai.com/account/api-keys) and your organization by navigating to [your organization page](https://platform.openai.com/account/org-settings).
Learn more about creating an OpenAI free trial at [this link](https://openai.com/pricing).
Do *not* check your key into source control.

When you run `azd up` after and are prompted to select a value for `openAiResourceGroupLocation`, you can select any location as it will not be used.


## Existing Azure AI Search resource

1. Run `azd env set AZURE_SEARCH_SERVICE {Name of existing Azure AI Search service}`
1. Run `azd env set AZURE_SEARCH_SERVICE_RESOURCE_GROUP {Name of existing resource group with ACS service}`
1. If that resource group is in a different location than the one you'll pick for the `azd up` step,
  then run `azd env set AZURE_SEARCH_SERVICE_LOCATION {Location of existing service}`
1. If the search service's SKU is not standard, then run `azd env set AZURE_SEARCH_SERVICE_SKU {Name of SKU}`. If you specify the free tier, then your app will no longer be able to use semantic ranker, and it will use keys instead of managed identity for accessing the search service. Be advised that [search SKUs cannot be changed](https://learn.microsoft.com/azure/search/search-sku-tier#tier-upgrade-or-downgrade). ([See other possible SKU values](https://learn.microsoft.com/azure/templates/microsoft.search/searchservices?pivots=deployment-language-bicep#sku))
1. If you have an existing index that is set up with all the expected fields, then run `azd env set AZURE_SEARCH_INDEX {Name of existing index}`. Otherwise, the `azd up` command will create a new index.

You can also customize the search service (new or existing) for non-English searches:

1. To configure the language of the search query to a value other than "en-US", run `azd env set AZURE_SEARCH_QUERY_LANGUAGE {Name of query language}`. ([See other possible values](https://learn.microsoft.com/rest/api/searchservice/preview-api/search-documents#queryLanguage))
1. To turn off the spell checker, run `azd env set AZURE_SEARCH_QUERY_SPELLER none`. Consult [this table](https://learn.microsoft.com/rest/api/searchservice/preview-api/search-documents#queryLanguage) to determine if spell checker is supported for your query language.
1. To configure the name of the analyzer to use for a searchable text field to a value other than "en.microsoft", run `azd env set AZURE_SEARCH_ANALYZER_NAME {Name of analyzer name}`. ([See other possible values](https://learn.microsoft.com/dotnet/api/microsoft.azure.search.models.field.analyzer?view=azure-dotnet-legacy&viewFallbackFrom=azure-dotnet))

## Existing Azure Document Intelligence resource

In order to support analysis of many document formats, this repository uses a preview version of Azure Document Intelligence (formerly Form Recognizer) that is only available in [limited regions](https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-layout).
If your existing resource is in one of those regions, then you can re-use it by setting the following environment variables:

1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_SERVICE {Name of existing Azure AI Document Intelligence service}`
1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_LOCATION {Location of existing service}`
1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_RESOURCE_GROUP {Name of resource group with existing service, defaults to main resource group}`
1. Run `azd env set AZURE_DOCUMENTINTELLIGENCE_SKU {SKU of existing service, defaults to S0}`

## Other existing Azure resources

You can also use existing Azure AI Document Intelligence and Storage Accounts. See `./infra/main.parameters.json` for list of environment variables to pass to `azd env set` to configure those existing resources.
