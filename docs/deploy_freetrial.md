# RAG chat: Deploying with a free trial account

If you have just created an Azure free trial account and are using the free trial credits,
there are several modifications you need to make, due to restrictions on the free trial account.

Follow these instructions *before* you run `azd up`.

## Accomodate for low OpenAI quotas

The free trial accounts currently get a max of 1K TPM (tokens-per-minute), whereas our Bicep templates try to allocate 30K TPM.

To reduce the TPM allocation, run these commands:

```shell
azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_CAPACITY 1
azd env set AZURE_OPENAI_EMB_DEPLOYMENT_CAPACITY 1
```

Alternatively, if you have an OpenAI.com account, you can use that instead:

```shell
azd env set OPENAI_HOST openai
azd env set OPENAI_ORGANIZATION {Your OpenAI organization}
azd env set OPENAI_API_KEY {Your OpenAI API key}
```

## Accomodate for Azure Container Apps restrictions

By default, this project deploys to Azure Container Apps, using a remote build process that builds the Docker image in the cloud.
Unfortunately, free trial accounts cannot use that remote build process.

You have two options:

1. Comment out or delete `remoteBuild: true` in `azure.yaml`, and make sure you have Docker installed in your environment.

2. Deploy using App Service instead:

    * Comment out `host: containerapp` and uncomment `host: appservice` in the [azure.yaml](../azure.yaml) file.
    * Set the deployment target to `appservice`:

        ```shell
        azd env set DEPLOYMENT_TARGET appservice
        ```
