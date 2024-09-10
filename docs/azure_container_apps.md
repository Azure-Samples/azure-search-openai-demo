# Deploying on Azure Container Apps

Due to [a limitation](https://github.com/Azure/azure-dev/issues/2736) of azd, the azure.yaml file for deploying to Azure Container Apps lives here.
To deploy to azure container apps, please run from project root folder:

```bash
cd containerapps
azd env new
azd env set DEPLOYMENT_TARGET containerapps
azd up
```

## Customizing Workload Profile

The default workload profile is Consumption. If you want to use a dedicated workload profile like D4, please run:

```bash
azd env AZURE_CONTAINER_APPS_WORKLOAD_PROFILE D4
```

For a full list of workload profiles, please check [here](https://learn.microsoft.com/azure/container-apps/workload-profiles-overview#profile-types).
Please note dedicated workload profiles have a different billing model than Consumption plan. Please check [here](https://learn.microsoft.com/azure/container-apps/billing) for details.
