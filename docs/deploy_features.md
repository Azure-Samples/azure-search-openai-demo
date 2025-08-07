# RAG chat: Enabling optional features

This document covers optional features that can be enabled in the deployed Azure resources.
You should typically enable these features before running `azd up`. Once you've set them, return to the [deployment steps](../README.md#deploying).

* [Using different chat completion models](#using-different-chat-completion-models)
* [Using reasoning models](#using-reasoning-models)
* [Using different embedding models](#using-different-embedding-models)
* [Enabling GPT vision feature](#enabling-gpt-vision-feature)
* [Enabling media description with Azure Content Understanding](#enabling-media-description-with-azure-content-understanding)
* [Enabling client-side chat history](#enabling-client-side-chat-history)
* [Enabling persistent chat history with Azure Cosmos DB](#enabling-persistent-chat-history-with-azure-cosmos-db)
* [Enabling language picker](#enabling-language-picker)
* [Enabling speech input/output](#enabling-speech-inputoutput)
* [Enabling Integrated Vectorization](#enabling-integrated-vectorization)
* [Enabling authentication](#enabling-authentication)
* [Enabling login and document level access control](#enabling-login-and-document-level-access-control)
* [Enabling user document upload](#enabling-user-document-upload)
* [Enabling CORS for an alternate frontend](#enabling-cors-for-an-alternate-frontend)
* [Enabling query rewriting](#enabling-query-rewriting)
* [Adding an OpenAI load balancer](#adding-an-openai-load-balancer)
* [Deploying with private endpoints](#deploying-with-private-endpoints)
* [Using local parsers](#using-local-parsers)

## Using different chat completion models

As of early June 2025, the default chat completion model is `gpt-4.1-mini`. If you deployed this sample before that date, the default model is `gpt-3.5-turbo` or `gpt-4o-mini`. You can change the chat completion model to any Azure OpenAI chat model that's available in your Azure OpenAI resource region by following these steps:

1. To set the name of the deployment, run this command with a unique name in your Azure OpenAI account. You can use any deployment name, as long as it's unique in your Azure OpenAI account. For convenience, many developers use the same deployment name as the model name, but this is not required.

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT <your-deployment-name>
    ```

    For example:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT gpt-5-chat
    ```

1. To set the GPT model to a different [available model](https://learn.microsoft.com/azure/ai-services/openai/concepts/models), run this command with the appropriate model name. For reasoning models like gpt-5/o3/o4, check [the reasoning guide](./reasoning.md)

   For gpt-5-chat:

   ```shell
   azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-5-chat
   ```

    For gpt-4.1-mini:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-4.1-mini
    ```

    For gpt-4o:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-4o
    ```

    For gpt-4o mini:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-4o-mini
    ```

    For gpt-4:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-4
    ```

    For gpt-3.5-turbo:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-35-turbo
    ```

1. To set the Azure OpenAI model version from the [available versions](https://learn.microsoft.com/azure/ai-services/openai/concepts/models), run this command with the appropriate version string.

   For gpt-5-chat:

   ```shell
   azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION 2025-08-07
   ```

    For gpt-4.1-mini:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION 2025-04-14
    ```

    For gpt-4o:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION 2024-05-13
    ```

    For gpt-4o mini:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION 2024-07-18
    ```

    For gpt-4:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION turbo-2024-04-09
    ```

    For gpt-3.5-turbo:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION 0125
    ```

1. To set the Azure OpenAI deployment SKU name, run this command with [the desired SKU name](https://learn.microsoft.com/azure/ai-services/openai/how-to/deployment-types#deployment-types).

    For GlobalStandard:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_SKU GlobalStandard
    ```

    For Standard:

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_SKU Standard
    ```

1. To set the Azure OpenAI deployment capacity (TPM, measured in thousands of tokens per minute), run this command with the desired capacity. This is not necessary if you are using the default capacity of 30.

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_CAPACITY 20
    ```

1. To update the deployment with the new parameters, run this command.

    ```bash
    azd up
    ```

This process does *not* delete your previous model deployment. If you want to delete previous deployments, go to your Azure OpenAI resource in Azure AI Foundry and delete it there.

> [!NOTE]
> To revert back to a previous model, run the same commands with the previous model name and version.

## Using reasoning models

⚠️ This feature is not currently compatible with [vision integration](./gpt4v.md).

This feature allows you to use reasoning models to generate responses based on retrieved content. These models spend more time processing and understanding the user's request.
To enable reasoning models, follow the steps in [the reasoning models guide](./reasoning.md).

## Using agentic retrieval

⚠️ This feature is not currently compatible with [vision integration](./gpt4v.md).

This feature allows you to use agentic retrieval in place of the Search API. To enable agentic retrieval, follow the steps in [the agentic retrieval guide](./agentic_retrieval.md)

## Using different embedding models

By default, the deployed Azure web app uses the `text-embedding-3-large` embedding model. If you want to use a different embedding model, you can do so by following these steps:

1. Run one of the following commands to set the desired model:

    ```shell
    azd env set AZURE_OPENAI_EMB_MODEL_NAME text-embedding-ada-002
    ```

    ```shell
    azd env set AZURE_OPENAI_EMB_MODEL_NAME text-embedding-3-small
    ```

    ```shell
    azd env set AZURE_OPENAI_EMB_MODEL_NAME text-embedding-3-large
    ```

2. Specify the desired dimensions of the model: (from 256-3072, model dependent)

    Default dimensions for text-embedding-ada-002

    ```shell
    azd env set AZURE_OPENAI_EMB_DIMENSIONS 1536
    ```

    Default dimensions for text-embedding-3-small

    ```shell
    azd env set AZURE_OPENAI_EMB_DIMENSIONS 1536
    ```

    Default dimensions for text-embedding-3-large

    ```shell
    azd env set AZURE_OPENAI_EMB_DIMENSIONS 3072
    ```

3. Set the model version, depending on the model you are using:

    For text-embedding-ada-002:

    ```shell
    azd env set AZURE_OPENAI_EMB_DEPLOYMENT_VERSION 2
    ```

    For text-embedding-3-small and text-embedding-3-large:

    ```shell
    azd env set AZURE_OPENAI_EMB_DEPLOYMENT_VERSION 1
    ```

4. To set the embedding model deployment SKU name, run this command with [the desired SKU name](https://learn.microsoft.com/azure/ai-services/openai/how-to/deployment-types#deployment-types).

    For GlobalStandard:

    ```bash
    azd env set AZURE_OPENAI_EMB_DEPLOYMENT_SKU GlobalStandard
    ```

    For Standard:

    ```bash
    azd env set AZURE_OPENAI_EMB_DEPLOYMENT_SKU Standard
    ```

5. When prompted during `azd up`, make sure to select a region for the OpenAI resource group location that supports the desired embedding model and deployment SKU. There are [limited regions available](https://learn.microsoft.com/azure/ai-services/openai/concepts/models?tabs=global-standard%2Cstandard-chat-completions#models-by-deployment-type).

If you have already deployed:

* You'll need to change the deployment name by running the appropriate commands for the model above.
* You'll need to create a new index, and re-index all of the data using the new model. You can either delete the current index in the Azure Portal, or create an index with a different name by running `azd env set AZURE_SEARCH_INDEX new-index-name`. When you next run `azd up`, the new index will be created. See the [data ingestion guide](./data_ingestion.md) for more details.

## Enabling GPT vision feature

⚠️ This feature is not currently compatible with [integrated vectorization](#enabling-integrated-vectorization).

This section covers the integration of GPT vision models with Azure AI Search. Learn how to enhance your search capabilities with the power of image and text indexing, enabling advanced search functionalities over diverse document types. For a detailed guide on setup and usage, visit our page on [Using GPT vision model with RAG approach](gpt4v.md).

## Enabling media description with Azure Content Understanding

⚠️ This feature is not currently compatible with [integrated vectorization](#enabling-integrated-vectorization).
It is compatible with [GPT vision integration](./gpt4v.md), but the features provide similar functionality.

By default, if your documents contain image-like figures, the data ingestion process will ignore those figures,
so users will not be able to ask questions about them.

You can optionably enable the description of media content using Azure Content Understanding. When enabled, the data ingestion process will send figures to Azure Content Understanding and replace the figure with the description in the indexed document.

To enable media description with Azure Content Understanding, run:

```shell
azd env set USE_MEDIA_DESCRIBER_AZURE_CU true
```

If you have already run `azd up`, you will need to run `azd provision` to create the new Content Understanding service.
If you have already indexed your documents and want to re-index them with the media descriptions,
first [remove the existing documents](./data_ingestion.md#removing-documents) and then [re-ingest the data](./data_ingestion.md#indexing-additional-documents).

⚠️ This feature does not yet support DOCX, PPTX, or XLSX formats. If you have figures in those formats, they will be ignored.
Convert them first to PDF or image formats to enable media description.

## Enabling client-side chat history

[📺 Watch: (RAG Deep Dive series) Storing chat history](https://www.youtube.com/watch?v=1YiTFnnLVIA)

This feature allows users to view the chat history of their conversation, stored in the browser using [IndexedDB](https://developer.mozilla.org/docs/Web/API/IndexedDB_API). That means the chat history will be available only on the device where the chat was initiated. To enable browser-stored chat history, run:

```shell
azd env set USE_CHAT_HISTORY_BROWSER true
```

## Enabling persistent chat history with Azure Cosmos DB

[📺 Watch: (RAG Deep Dive series) Storing chat history](https://www.youtube.com/watch?v=1YiTFnnLVIA)

This feature allows authenticated users to view the chat history of their conversations, stored in the server-side storage using [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/).This option requires that authentication be enabled. The chat history will be persistent and accessible from any device where the user logs in with the same account. To enable server-stored chat history, run:

```shell
azd env set USE_CHAT_HISTORY_COSMOS true
```

When both the browser-stored and Cosmos DB options are enabled, Cosmos DB will take precedence over browser-stored chat history.

## Enabling language picker

You can optionally enable the language picker to allow users to switch between different languages. Currently, it supports English, Spanish, French, and Japanese.

To add support for additional languages, create new locale files and update `app/frontend/src/i18n/config.ts` accordingly. To enable language picker, run:

```shell
azd env set ENABLE_LANGUAGE_PICKER true
```

## Enabling speech input/output

[📺 Watch a short video of speech input/output](https://www.youtube.com/watch?v=BwiHUjlLY_U)

You can optionally enable speech input/output by setting the azd environment variables.

### Speech Input

The speech input feature uses the browser's built-in [Speech Recognition API](https://developer.mozilla.org/docs/Web/API/SpeechRecognition). It may not work in all browser/OS combinations. To enable speech input, run:

```shell
azd env set USE_SPEECH_INPUT_BROWSER true
```

### Speech Output

The speech output feature uses [Azure Speech Service](https://learn.microsoft.com/azure/ai-services/speech-service/overview) for speech-to-text. Additional costs will be incurred for using the Azure Speech Service. [See pricing](https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/). To enable speech output, run:

```shell
azd env set USE_SPEECH_OUTPUT_AZURE true
```

To set [the voice](https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts) for the speech output, run:

```shell
azd env set AZURE_SPEECH_SERVICE_VOICE en-US-AndrewMultilingualNeural
```

Alternatively you can use the browser's built-in [Speech Synthesis API](https://developer.mozilla.org/docs/Web/API/SpeechSynthesis). It may not work in all browser/OS combinations. To enable speech output, run:

```shell
azd env set USE_SPEECH_OUTPUT_BROWSER true
```

## Enabling Integrated Vectorization

⚠️ This feature is not currently compatible with the [GPT vision integration](./gpt4v.md).

Azure AI search recently introduced an [integrated vectorization feature in preview mode](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/announcing-the-public-preview-of-integrated-vectorization-in-azure-ai-search/3960809). This feature is a cloud-based approach to data ingestion, which takes care of document format cracking, data extraction, chunking, vectorization, and indexing, all with Azure technologies.

To enable integrated vectorization with this sample:

1. If you've previously deployed, delete the existing search index. 🗑️
2. To enable the use of integrated vectorization, run:

    ```shell
    azd env set USE_FEATURE_INT_VECTORIZATION true
    ```

3. If you've already deployed your app, then you can run just the `provision` step:

    ```shell
    azd provision
    ```

    That will set up necessary RBAC roles and configure the integrated vectorization feature on your search service.

    If you haven't deployed your app yet, then you should run the full `azd up` after configuring all optional features.

4. You can view the resources such as the indexer and skillset in Azure Portal and monitor the status of the vectorization process.

## Enabling authentication

By default, the deployed Azure web app will have no authentication or access restrictions enabled, meaning anyone with routable network access to the web app can chat with your indexed data. If you'd like to automatically setup authentication and user login as part of the `azd up` process, see [this guide](./login_and_acl.md).

Alternatively, you can manually require authentication to your Azure Active Directory by following the [Add app authentication](https://learn.microsoft.com/azure/app-service/scenario-secure-app-authentication-app-service) tutorial and set it up against the deployed web app.

To then limit access to a specific set of users or groups, you can follow the steps from [Restrict your Microsoft Entra app to a set of users](https://learn.microsoft.com/entra/identity-platform/howto-restrict-your-app-to-a-set-of-users) by changing "Assignment Required?" option under the Enterprise Application, and then assigning users/groups access.  Users not granted explicit access will receive the error message -AADSTS50105: Your administrator has configured the application <app_name> to block users unless they are specifically granted ('assigned') access to the application.-

## Enabling login and document level access control

By default, the deployed Azure web app allows users to chat with all your indexed data. You can enable an optional login system using Azure Active Directory to restrict access to indexed data based on the logged in user. Enable the optional login and document level access control system by following [this guide](./login_and_acl.md).

## Enabling user document upload

You can enable an optional user document upload system to allow users to upload their own documents and chat with them. This feature requires you to first [enable login and document level access control](./login_and_acl.md). Then you can enable the optional user document upload system by setting an azd environment variable:

`azd env set USE_USER_UPLOAD true`

Then you'll need to run `azd up` to provision an Azure Data Lake Storage Gen2 account for storing the user-uploaded documents.
When the user uploads a document, it will be stored in a directory in that account with the same name as the user's Entra object id,
and will have ACLs associated with that directory. When the ingester runs, it will also set the `oids` of the indexed chunks to the user's Entra object id.

If you are enabling this feature on an existing index, you should also update your index to have the new `storageUrl` field:

```shell
python ./scripts/manageacl.py  -v --acl-action enable_acls
```

And then update existing search documents with the storage URL of the main Blob container:

```shell
python ./scripts/manageacl.py  -v --acl-action update_storage_urls --url <https://YOUR-MAIN-STORAGE-ACCOUNT.blob.core.windows.net/content/>
```

Going forward, all uploaded documents will have their `storageUrl` set in the search index.
This is necessary to disambiguate user-uploaded documents from admin-uploaded documents.

## Enabling CORS for an alternate frontend

By default, the deployed Azure web app will only allow requests from the same origin.  To enable CORS for a frontend hosted on a different origin, run:

1. Run `azd env set ALLOWED_ORIGIN https://<your-domain.com>`
2. Run `azd up`

For the frontend code, change `BACKEND_URI` in `api.ts` to point at the deployed backend URL, so that all fetch requests will be sent to the deployed backend.

For an alternate frontend that's written in Web Components and deployed to Static Web Apps, check out
[azure-search-openai-javascript](https://github.com/Azure-Samples/azure-search-openai-javascript) and its guide
on [using a different backend](https://github.com/Azure-Samples/azure-search-openai-javascript#using-a-different-backend).
Both these repositories adhere to the same [HTTP protocol for AI chat apps](https://aka.ms/chatprotocol).

## Enabling query rewriting

By default, the [query rewriting feature](https://learn.microsoft.com/azure/search/semantic-how-to-query-rewrite) from the Azure AI Search service is not enabled. Note that the search service query rewriting feature is different from the query rewriting step that is used by the Chat tab in the codebase. The in-repo query rewriting step also incorporates conversation history, while the search service query rewriting feature only considers the query itself. To enable search service query rewriting, set the following environment variables:

1. Check that your Azure AI Search service is using one of the [supported regions](https://learn.microsoft.com/azure/search/semantic-how-to-query-rewrite#prerequisites) for query rewriting.
1. Ensure semantic ranker is enabled. Query rewriting may only be used with semantic ranker. Run `azd env set AZURE_SEARCH_SEMANTIC_RANKER free` or `azd env set AZURE_SEARCH_SEMANTIC_RANKER standard` depending on your desired [semantic ranker tier](https://learn.microsoft.com/azure/search/semantic-how-to-configure).
1. Enable query rewriting. Run `azd env set AZURE_SEARCH_QUERY_REWRITING true`. An option in developer settings will appear allowing you to toggle query rewriting on and off. It will be on by default.

## Adding an OpenAI load balancer

As discussed in more details in our [productionizing guide](./productionizing.md), you may want to consider implementing a load balancer between OpenAI instances if you are consistently going over the TPM limit.
Fortunately, this repository is designed for easy integration with other repositories that create load balancers for OpenAI instances. For seamless integration instructions with this sample, please check:

* [Scale Azure OpenAI for Python with Azure API Management](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-scaling-with-azure-api-management)
* [Scale Azure OpenAI for Python chat using RAG with Azure Container Apps](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-scaling-with-azure-container-apps)

## Deploying with private endpoints

It is possible to deploy this app with public access disabled, using Azure private endpoints and private DNS Zones. For more details, read [the private deployment guide](./deploy_private.md). That requires a multi-stage provisioning, so you will need to do more than just `azd up` after setting the environment variables.

## Using local parsers

If you want to decrease the charges by using local parsers instead of Azure Document Intelligence, you can set environment variables before running the [data ingestion script](./data_ingestion.md). Note that local parsers will generally be not as sophisticated.

1. Run `azd env set USE_LOCAL_PDF_PARSER true` to use the local PDF parser.
1. Run `azd env set USE_LOCAL_HTML_PARSER true` to use the local HTML parser.

The local parsers will be used the next time you run the data ingestion script. To use these parsers for the user document upload system, you'll need to run `azd provision` to update the web app to use the local parsers.
