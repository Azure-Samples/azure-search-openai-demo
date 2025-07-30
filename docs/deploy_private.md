<!--
---
name: RAG chat with private endpoints
description: Configure access to a chat app so that it's only accessible from private endpoints.
languages:
- python
- typescript
- bicep
- azdeveloper
products:
- azure-openai
- azure-cognitive-search
- azure-app-service
- azure
page_type: sample
urlFragment: azure-search-openai-demo-private-access
---
-->

# RAG chat: Deploying with private access

[📺 Watch: (RAG Deep Dive series) Private network deployment](https://www.youtube.com/watch?v=08wtL1eB15g)

The [azure-search-openai-demo](/) project can set up a full RAG chat app on Azure AI Search and OpenAI so that you can chat on custom data, like internal enterprise data or domain-specific knowledge sets. For full instructions on setting up the project, consult the [main README](/README.md), and then return here for detailed instructions on configuring private endpoints.

⚠️ This feature is not yet compatible with Azure Container Apps, so you will need to [deploy to Azure App Service](./azure_app_service.md) instead.

If you want to disable public access when deploying the Chat App, you can do so by setting `azd` environment values.

## Before you begin

Deploying with public access disabled adds additional cost to your deployment. Please see pricing for the following products:

1. [Private Endpoints](https://azure.microsoft.com/pricing/details/private-link/)
    1. The exact number of private endpoints created depends on the [optional features](./deploy_features.md) used.
1. [Private DNS Zones](https://azure.microsoft.com/pricing/details/dns/)

## Environment variables controlling private access

1. `AZURE_PUBLIC_NETWORK_ACCESS`: Controls the value of public network access on supported Azure resources. Valid values are 'Enabled' or 'Disabled'.
    1. When public network access is 'Enabled', Azure resources are open to the internet.
    1. When public network access is 'Disabled', Azure resources are only accessible over a virtual network.
1. `AZURE_USE_PRIVATE_ENDPOINT`: Controls deployment of [private endpoints](https://learn.microsoft.com/azure/private-link/private-endpoint-overview) which connect Azure resources to the virtual network.
    1. When set to 'true', ensures private endpoints are deployed for connectivity even when `AZURE_PUBLIC_NETWORK_ACCESS` is 'Disabled'.
    1. Note that private endpoints do not make the chat app accessible from the internet. Connections must be initiated from inside the virtual network.

## Recommended deployment strategy for private access

1. Configure the azd environment variables to use private endpoints and a VPN gateway, with public network access disabled. This will allow you to connect to the chat app from inside the virtual network, but not from the public Internet.

    ```shell
    azd env set AZURE_USE_PRIVATE_ENDPOINT true
    azd env set AZURE_USE_VPN_GATEWAY true
    azd env set AZURE_PUBLIC_NETWORK_ACCESS Disabled
    azd up
    ```

2. Provision all the Azure resources:

    ```bash
    azd provision
    ```

3. Once provisioning is complete, you will see an error when it tries to run the data ingestion script, because you are not yet connected to the VPN. That message should provide a URL for the VPN configuration file download. If you don't see that URL, run this command:

    ```bash
    azd env get-value AZURE_VPN_CONFIG_DOWNLOAD_LINK
    ```

    Open that link in your browser. Select "Download VPN client" to download a ZIP file containing the VPN configuration.

4. Open `AzureVPN/azurevpnconfig.xml`, and replace the `<clientconfig>` empty tag with the following:

    ```xml
      <clientconfig>
        <dnsservers>
          <dnsserver>10.0.11.4</dnsserver>
        </dnsservers>
      </clientconfig>
    ```

5. Install the [Azure VPN Client](https://learn.microsoft.com/azure/vpn-gateway/azure-vpn-client-versions).

6. Open the Azure VPN Client and select "Import" button. Select the `azurevpnconfig.xml` file you just downloaded and modified.

7. Select "Connect" and the new VPN connection. You will be prompted to select your Microsoft account and login.

8. Once you're successfully connected to VPN, you can run the data ingestion script:

    ```bash
    azd hooks run postprovision
    ```

9. Finally, you can deploy the app:

    ```bash
    azd deploy
    ```
