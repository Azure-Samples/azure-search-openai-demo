# Alternative RAG chat samples

There are an increasingly large number of ways to build RAG chat apps.

## Other language samples

Inspired by this repo, there are similar apps for other languages:

* [**JavaScript**](https://aka.ms/azai/js/code)
* [**.NET**](https://aka.ms/azai/net/code)
* [**Java**](https://aka.ms/azai/java/code)

They do not all support the same features as this repo, but they provide a good starting point for building a RAG chat app in your preferred language.

## Other Python samples

Another popular repository for this use case is here:
https://github.com/Microsoft/sample-app-aoai-chatGPT/

That repository is designed for use by customers using Azure OpenAI studio and Azure Portal for setup. It also includes `azd` support for folks who want to deploy it completely from scratch.

The primary differences:

* This repository includes multiple RAG (retrieval-augmented generation) approaches that chain the results of multiple API calls (to Azure OpenAI and ACS) together in different ways. The other repository uses only the built-in data sources option for the ChatCompletions API, which uses a RAG approach on the specified ACS index. That should work for most uses, but if you needed more flexibility, this sample may be a better option.
* This repository is also a bit more experimental in other ways, since it's not tied to the Azure OpenAI Studio like the other repository.

Feature comparison:

| Feature | azure-search-openai-demo | sample-app-aoai-chatGPT |
| --- | --- | --- |
| RAG approach | Multiple approaches | Only via ChatCompletion API data_sources |
| Vector support | ✅ Yes | ✅ Yes |
| Data ingestion | ✅ Yes ([Many formats](data_ingestion.md#supported-document-formats)) | ✅ Yes ([Many formats](https://learn.microsoft.com/azure/ai-services/openai/concepts/use-your-data?tabs=ai-search#data-formats-and-file-types)) |
| Persistent chat history | ❌ No (browser tab only) | ✅ Yes, in CosmosDB |
| User feedback | ❌ No | ✅ Yes |
| GPT-4-vision |  ✅ Yes | ❌ No |
| Auth + ACL |  ✅ Yes | ✅ Yes |

Technology comparison:

| Tech | azure-search-openai-demo | sample-app-aoai-chatGPT |
| --- | --- | --- |
| Frontend | React | React |
| Backend | Python (Quart) | Python (Quart) |
| Vector DB | Azure AI Search | Azure AI Search, CosmosDB Mongo vCore, ElasticSearch, Pinecone, AzureML |
| Deployment | Azure Developer CLI (azd) | Azure Portal, az, azd |
