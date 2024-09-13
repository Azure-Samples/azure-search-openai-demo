# Deploying on Azure Container Apps

Due to [a limitation](https://github.com/Azure/azure-dev/issues/2736) of the Azure Developer CLI (`azd`), there can be only one host option in the [azure.yaml](../azure.yaml) file.
By default, `host: appservice` is used and `host: containerapp` is commented out.

To deploy to Azure Container Apps, please follow the following steps:

1. Comment out `host: appservice` and uncomment `host: containerapp` in the [azure.yaml](../azure.yaml) file.

1. Run

```bash
# Login to your azure account
azd auth login

# Create a new env 
azd env new
# Set deployment target to containerapps
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
