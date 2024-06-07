
# Enabling optional features

This document covers optional features that can be enabled in the deployed Azure resources.
You should typically enable these features before running `azd up`. Once you've set them, return to the [deployment steps](../README.md#deploying).

* [Using GPT-4](#using-gpt-4)
* [Using text-embedding-3 models](#using-text-embedding-3-models)
* [Enabling GPT-4 Turbo with Vision](#enabling-gpt-4-turbo-with-vision)
* [Enabling speech input/output](#enabling-speech-inputoutput)
* [Enabling Integrated Vectorization](#enabling-integrated-vectorization)
* [Enabling authentication](#enabling-authentication)
* [Enabling login and document level access control](#enabling-login-and-document-level-access-control)
* [Enabling user document upload](#enabling-user-document-upload)
* [Enabling CORS for an alternate frontend](#enabling-cors-for-an-alternate-frontend)
* [Adding an OpenAI load balancer](#adding-an-openai-load-balancer)
* [Deploying with private endpoints](#deploying-with-private-endpoints)
* [Using local parsers](#using-local-parsers)

## Using GPT-4

We generally find that most developers are able to get high quality answers using GPT 3.5. However, if you want to try GPT-4, you can do so by following these steps:

Execute the following commands inside your terminal:

1. To set the name of the deployment, run this command with a new unique name.

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT chat4
    ```

1. To set the GPT model name to a **gpt-4** version from the [available models](https://learn.microsoft.com/azure/ai-services/openai/concepts/models), run this command with the appropriate gpt model name.

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-4
    ```

1. To set the Azure OpenAI deployment capacity, run this command with the desired capacity.

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_CAPACITY 10
    ```

1. To set the Azure OpenAI deployment version from the [available versions](https://learn.microsoft.com/azure/ai-services/openai/concepts/models), run this command with the appropriate version.

    ```bash
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION turbo-2024-04-09
    ```

1. To update the deployment with the new parameters, run this command.

    ```bash
    azd up
    ```

> [!NOTE]
> To revert back to GPT 3.5, run the following commands:
>
> * `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT chat` to set the name of your old GPT 3.5 deployment.
> * `azd env set AZURE_OPENAI_CHATGPT_MODEL gpt-35-turbo` to set the name of your old GPT 3.5 model.
> * `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_CAPACITY 30` to set the capacity of your old GPT 3.5 deployment.
> * `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION 0613` to set the version number of your old GPT 3.5.
> * `azd up` to update the provisioned resources.
>
> Note that this does not delete your GPT-4 deployment; it just makes your application create a new or reuse an old GPT 3.5 deployment. If you want to delete it, you can go to your Azure OpenAI studio and do so.

## Using text-embedding-3 models

By default, the deployed Azure web app uses the `text-embedding-ada-002` embedding model. If you want to use one of the text-embedding-3 models, you can do so by following these steps:

1. Run one of the following commands to set the desired model:

    ```shell
    azd env set AZURE_OPENAI_EMB_MODEL_NAME text-embedding-3-small
    ```

    ```shell
    azd env set AZURE_OPENAI_EMB_MODEL_NAME text-embedding-3-large
    ```

2. Specify the desired dimensions of the model: (from 256-3072, model dependent)

    ```shell
    azd env set AZURE_OPENAI_EMB_DIMENSIONS 256
    ```

3. Set the model version to "1" (the only version as of March 2024):

    ```shell
    azd env set AZURE_OPENAI_EMB_DEPLOYMENT_VERSION 1
    ```

4. When prompted during `azd up`, make sure to select a region for the OpenAI resource group location that supports the text-embedding-3 models. There are [limited regions available](https://learn.microsoft.com/azure/ai-services/openai/concepts/models#embeddings-models).

If you have already deployed:

* You'll need to change the deployment name by running `azd env set AZURE_OPENAI_EMB_DEPLOYMENT <new-deployment-name>`
* You'll need to create a new index, and re-index all of the data using the new model. You can either delete the current index in the Azure Portal, or create an index with a different name by running `azd env set AZURE_SEARCH_INDEX new-index-name`. When you next run `azd up`, the new index will be created and the data will be re-indexed.
* If your OpenAI resource is not in one of the supported regions, you should delete `openAiResourceGroupLocation` from `.azure/YOUR-ENV-NAME/config.json`. When running `azd up`, you will be prompted to select a new region.

> ![NOTE]
> The text-embedding-3 models are not currently supported by the integrated vectorization feature.

## Enabling GPT-4 Turbo with Vision

This section covers the integration of GPT-4 Vision with Azure AI Search. Learn how to enhance your search capabilities with the power of image and text indexing, enabling advanced search functionalities over diverse document types. For a detailed guide on setup and usage, visit our [Enabling GPT-4 Turbo with Vision](gpt4v.md) page.

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

Azure AI search recently introduced an [integrated vectorization feature in preview mode](https://techcommunity.microsoft.com/t5/ai-azure-ai-services-blog/announcing-the-public-preview-of-integrated-vectorization-in/ba-p/3960809#:~:text=Integrated%20vectorization%20is%20a%20new%20feature%20of%20Azure,pull-indexers%2C%20and%20vectorization%20of%20text%20queries%20through%20vectorizers). This feature is a cloud-based approach to data ingestion, which takes care of document format cracking, data extraction, chunking, vectorization, and indexing, all with Azure technologies.

To enable integrated vectorization with this sample:

1. If you've previously deployed, delete the existing search index.
2. Run `azd env set USE_FEATURE_INT_VECTORIZATION true`
3. Run `azd up` to update system and user roles
4. You can view the resources such as the indexer and skillset in Azure Portal and monitor the status of the vectorization process.

This feature is not currently compatible with GPT4-vision or the newer text-embedding-3 models.

## Enabling authentication

By default, the deployed Azure web app will have no authentication or access restrictions enabled, meaning anyone with routable network access to the web app can chat with your indexed data. If you'd like to automatically setup authentication and user login as part of the `azd up` process, see [this guide](./login_and_acl.md).

Alternatively, you can manually require authentication to your Azure Active Directory by following the [Add app authentication](https://learn.microsoft.com/azure/app-service/scenario-secure-app-authentication-app-service) tutorial and set it up against the deployed web app.

To then limit access to a specific set of users or groups, you can follow the steps from [Restrict your Microsoft Entra app to a set of users](https://learn.microsoft.com/entra/identity-platform/howto-restrict-your-app-to-a-set-of-users) by changing "Assignment Required?" option under the Enterprise Application, and then assigning users/groups access.  Users not granted explicit access will receive the error message -AADSTS50105: Your administrator has configured the application <app_name> to block users unless they are specifically granted ('assigned') access to the application.-

## Enabling login and document level access control

By default, the deployed Azure web app allows users to chat with all your indexed data. You can enable an optional login system using Azure Active Directory to restrict access to indexed data based on the logged in user. Enable the optional login and document level access control system by following [this guide](./login_and_acl.md).

## Enabling user document upload

You can enable an optional user document upload system to allow users to upload their own documents and chat with them. This feature requires you to first [enable login and document level access control](docs/login_and_acl.md). Then you can enable the optional user document upload system by setting an azd environment variable:

`azd env set USE_USER_UPLOAD true`

Then you'll need to run `azd up` to provision an Azure Data Lake Storage Gen2 account for storing the user-uploaded documents.
When the user uploads a document, it will be stored in a directory in that account with the same name as the user's Entra object id,
and will have ACLs associated with that directory. When the ingester runs, it will also set the `oids` of the indexed chunks to the user's Entra object id.

If you are enabling this feature on an existing index, you should also update your index to have the new `storageUrl` field:

```shell
./scripts/manageacl.ps1  -v --acl-action enable_acls
```

And then update existing search documents with the storage URL of the main Blob container:

```shell
./scripts/manageacl.ps1  -v --acl-action update_storage_urls --url <https://YOUR-MAIN-STORAGE-ACCOUNT.blob.core.windows.net/content/>
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

## Adding an OpenAI load balancer

As discussed in more details in our [productionizing guide](docs/productionizing.md), you may want to consider implementing a load balancer between OpenAI instances if you are consistently going over the TPM limit.
Fortunately, this repository is designed for easy integration with other repositories that create load balancers for OpenAI instances. For seamless integration instructions with this sample, please check:

* [Scale Azure OpenAI for Python with Azure API Management](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-scaling-with-azure-api-management)
* [Scale Azure OpenAI for Python chat using RAG with Azure Container Apps](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-scaling-with-azure-container-apps)

## Deploying with private endpoints

It is possible to deploy this app with public access disabled, using Azure private endpoints and private DNS Zones. For more details, read [the private deployment guide](docs/deploy_private.md). That requires a multi-stage provisioning, so you will need to do more than just `azd up` after setting the environment variables.

## Using local parsers

If you want to decrease the charges by using local parsers instead of Azure Document Intelligence, you can set environment variables before running the [data ingestion script](./data_ingestion.md). Note that local parsers will generally be not as sophisticated.

1. Run `azd env set USE_LOCAL_PDF_PARSER true` to use the local PDF parser.
1. Run `azd env set USE_LOCAL_HTML_PARSER true` to use the local HTML parser.

The local parsers will be used the next time you run the data ingestion script. To use these parsers for the user document upload system, you'll need to run `azd provision` to update the web app to use the local parsers.
