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

1. Deploy the app with private endpoints enabled and public access enabled.

  ```shell
  azd env set AZURE_USE_PRIVATE_ENDPOINT true
  azd env set AZURE_PUBLIC_NETWORK_ACCESS Enabled
  azd up
  ```

1. Validate that you can connect to the chat app and it's working as expected from the internet.
1. Re-provision the app with public access disabled.

  ```shell
  azd env set AZURE_PUBLIC_NETWORK_ACCESS Disabled
  azd provision
  ```

1. Log into your network using a tool like [Azure VPN Gateway](https://azure.microsoft.com/services/vpn-gateway/) and validate that you can connect to the chat app from inside the network.
