# RAG chat: Alternative RAG chat samples

There are an increasingly large number of ways to build RAG chat apps.

## Other language samples

Inspired by this repo, there are similar apps for other languages:

* [**JavaScript**](https://aka.ms/azai/js/code)
* [**.NET**](https://aka.ms/azai/net/code)
* [**Java**](https://aka.ms/azai/java/code)

They do not all support the same features as this repo, but they provide a good starting point for building a RAG chat app in your preferred language.

## JavaScript/TypeScript samples

### AzureChat

Another popular repository for chat applications is:
[https://github.com/microsoft/azurechat](https://github.com/microsoft/azurechat)

AzureChat is a JavaScript/TypeScript-based application that focuses on providing a personal ChatGPT-like experience. While it uses similar Azure services, it differs significantly in technology stack and use case focus.

The primary differences:

* **Technology Stack**: AzureChat uses a JavaScript/TypeScript codebase with a Node.js backend, while this repository uses Python (Quart) for the backend.
* **Use Case Focus**: AzureChat is designed more like a ChatGPT clone for personal use, whereas this repository focuses on chat-on-business-data scenarios for enterprise use.
* **Security Approach**: AzureChat stores secrets in Key Vault, while this repository uses keyless authentication with managed identities.
* **Feature Set**: AzureChat has more personal-use features but fewer enterprise features compared to this repository.

Feature comparison:

| Feature | azure-search-openai-demo | azurechat |
| --- | --- | --- |
| Use case focus | Enterprise chat-on-business-data | Personal ChatGPT-like experience |
| RAG approach | Multiple approaches | ChatGPT-style with RAG |
| Vector support | ✅ Yes | ✅ Yes |
| Data ingestion | ✅ Yes ([Many formats](data_ingestion.md#supported-document-formats)) | ✅ Yes |
| Persistent chat history | ✅ Yes | ✅ Yes |
| User feedback | ❌ No | ✅ Yes |
| GPT-4-vision | ✅ Yes | ✅ Yes |
| Voice/Speech I/O | ✅ Yes | ✅ Yes |
| File upload | ✅ Yes | ✅ Yes |
| Auth + ACL | ✅ Yes (Enterprise-focused) | ✅ Yes (Personal-focused) |
| Access control | ✅ Yes (Document-level) | ❌ Limited |

Technology comparison:

| Tech | azure-search-openai-demo | azurechat |
| --- | --- | --- |
| Frontend | React (TypeScript) | React (TypeScript) |
| Backend | Python (Quart) | Node.js (TypeScript) |
| Database | Azure AI Search | Azure AI Search |
| Authentication | Managed Identity (Keyless) | Key Vault |
| Deployment | Azure Developer CLI (azd) | Azure Developer CLI (azd) |

## Other Python samples

Another popular repository for this use case is here:
[https://github.com/Microsoft/sample-app-aoai-chatGPT/](https://github.com/Microsoft/sample-app-aoai-chatGPT/)

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
| Persistent chat history | ✅ Yes | ✅ Yes |
| User feedback | ❌ No | ✅ Yes |
| GPT-4-vision |  ✅ Yes | ❌ No |
| Auth + ACL |  ✅ Yes | ✅ Yes |
| User upload |  ✅ Yes | ❌ No |
| Speech I/O | ✅ Yes | ❌ No |

Technology comparison:

| Tech | azure-search-openai-demo | sample-app-aoai-chatGPT |
| --- | --- | --- |
| Frontend | React | React |
| Backend | Python (Quart) | Python (Quart) |
| Vector DB | Azure AI Search | Azure AI Search, CosmosDB Mongo vCore, ElasticSearch, Pinecone, AzureML |
| Deployment | Azure Developer CLI (azd) | Azure Portal, az, azd |
