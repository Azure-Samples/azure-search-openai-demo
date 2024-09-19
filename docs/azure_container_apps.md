# Deploying on Azure Container Apps

Due to [a limitation](https://github.com/Azure/azure-dev/issues/2736) of the Azure Developer CLI (`azd`), there can be only one host option in the [azure.yaml](../azure.yaml) file.
By default, `host: appservice` is used and `host: containerapp` is commented out.

To deploy to Azure Container Apps, please follow the following steps:

1. Comment out `host: appservice` and uncomment `host: containerapp` in the [azure.yaml](../azure.yaml) file.

2. Login to your Azure account:

    ```bash
    azd auth login
    ```

3. Create a new `azd` environment to store the deployment parameters:

    ```bash
    azd env new
    ```

    Enter a name that will be used for the resource group.
    This will create a new folder in the `.azure` folder, and set it as the active environment for any calls to `azd` going forward.

4. Set the deployment target to `containerapps`:

    ```bash
    azd env set DEPLOYMENT_TARGET containerapps
    ```

5. (Optional) This is the point where you can customize the deployment by setting other `azd1 environment variables, in order to [use existing resources](docs/deploy_existing.md), [enable optional features (such as auth or vision)](docs/deploy_features.md), or [deploy to free tiers](docs/deploy_lowcost.md).
6. Provision the resources and deploy the code:

    ```bash
    azd up
    ```

    This will provision Azure resources and deploy this sample to those resources, including building the search index based on the files found in the `./data` folder.

    **Important**: Beware that the resources created by this command will incur immediate costs, primarily from the AI Search resource. These resources may accrue costs even if you interrupt the command before it is fully executed. You can run `azd down` or delete the resources manually to avoid unnecessary spending.

## Customizing Workload Profile

The default workload profile is Consumption. If you want to use a dedicated workload profile like D4, please run:

```bash
azd env AZURE_CONTAINER_APPS_WORKLOAD_PROFILE D4
```

For a full list of workload profiles, please check [here](https://learn.microsoft.com/azure/container-apps/workload-profiles-overview#profile-types).
Please note dedicated workload profiles have a different billing model than Consumption plan. Please check [here](https://learn.microsoft.com/azure/container-apps/billing) for details.

## Private endpoints

Private endpoints is still in private preview for Azure Conainer Apps and not supported for now.
