
# Deploying with private access

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
