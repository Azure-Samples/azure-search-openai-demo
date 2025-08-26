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

If you want to disable public access for the application so that it can only be access from a private network, follow this guide.

## Before you begin

Deploying with private networking adds additional cost to your deployment. Please see pricing for the following products:

* [Azure Container Registry](https://azure.microsoft.com/pricing/details/container-registry/): Premium tier is used when virtual network is added (required for private links), which incurs additional costs.
* [Azure Container Apps](https://azure.microsoft.com/pricing/details/container-apps/): Workload profiles environment is used when virtual network is added (required for private links), which incurs additional costs. Additionally, min replica count is set to 1, so you will be charged for at least one instance.
* [VPN Gateway](https://azure.microsoft.com/pricing/details/vpn-gateway/): VpnGw2 SKU. Pricing includes a base monthly cost plus an hourly cost based on the number of connections.
* [Virtual Network](https://azure.microsoft.com/pricing/details/virtual-network/): Pay-as-you-go tier. Costs based on data processed.

The pricing for the following features depends on the [optional features](./deploy_features.md) used. Most deployments will have at least 5 private endpoints (Azure OpenAI, Azure Cognitive Services, Azure AI Search, Azure Blob Storage, and either Azure App Service or Azure Container Apps).

* [Azure Private Endpoints](https://azure.microsoft.com/pricing/details/private-link/): Pricing is per hour per endpoint.
* [Private DNS Zones](https://azure.microsoft.com/pricing/details/dns/): Pricing is per month and zones.
* [Azure Private DNS Resolver](https://azure.microsoft.com/pricing/details/dns/): Pricing is per month and zones.

⚠️ To avoid unnecessary costs, remember to take down your app if it's no longer in use,
either by deleting the resource group in the Portal or running `azd down`.
You might also decide to delete the VPN Gateway when not in use.

## Deployment steps for private access

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

    > **Note:** We use the IP address `10.0.11.4` since it is the first available IP in the `dns-resolver-subnet`(10.0.11.0/28) from the provisioned virtual network, as Azure reserves the first four IP addresses in each subnet. Adding this DNS server allows your VPN client to resolve private DNS names for Azure services accessed through private endpoints. See the network configuration in [network-isolation.bicep](../infra/network-isolation.bicep) for details.

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

## Environment variables controlling private access

1. `AZURE_PUBLIC_NETWORK_ACCESS`: Controls the value of public network access on supported Azure resources. Valid values are 'Enabled' or 'Disabled'.
    1. When public network access is 'Enabled', Azure resources are open to the internet.
    1. When public network access is 'Disabled', Azure resources are only accessible over a virtual network.
1. `AZURE_USE_PRIVATE_ENDPOINT`: Controls deployment of [private endpoints](https://learn.microsoft.com/azure/private-link/private-endpoint-overview) which connect Azure resources to the virtual network.
    1. When set to 'true', ensures private endpoints are deployed for connectivity even when `AZURE_PUBLIC_NETWORK_ACCESS` is 'Disabled'.
    1. Note that private endpoints do not make the chat app accessible from the internet. Connections must be initiated from inside the virtual network.
1. `AZURE_USE_VPN_GATEWAY`: Controls deployment of a VPN gateway for the virtual network. If you do not use this and public access is disabled, you will need a different way to connect to the virtual network.

## Compatibility with other features

* **GitHub Actions / Azure DevOps**: The private access deployment is not compatible with the built-in CI/CD pipelines, as it requires a VPN connection to deploy the app. You could modify the pipeline to only do provisioning, and set up a different deployment strategy for the app.
