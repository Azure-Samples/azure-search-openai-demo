# RAG chat: Deploying on Azure App Service

Due to [a limitation](https://github.com/Azure/azure-dev/issues/2736) of the Azure Developer CLI (`azd`), there can be only one host option in the [azure.yaml](../azure.yaml) file.
By default, `host: containerapp` is used and `host: appservice` is commented out.

To deploy to Azure App Service, please follow the following steps:

1. Comment out `host: containerapp` and uncomment `host: appservice` in the [azure.yaml](../azure.yaml) file.

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

4. Set the deployment target to `appservice`:

    ```bash
    azd env set DEPLOYMENT_TARGET appservice
    ```

5. (Optional) This is the point where you can customize the deployment by setting other `azd` environment variables, in order to [use existing resources](deploy_existing.md), [enable optional features (such as auth or vision)](deploy_features.md), or [deploy to free tiers](deploy_lowcost.md).
6. Provision the resources and deploy the code:

    ```bash
    azd up
    ```

    This will provision Azure resources and deploy this sample to those resources, including building the search index based on the files found in the `./data` folder.

    **Important**: Beware that the resources created by this command will incur immediate costs, primarily from the AI Search resource. These resources may accrue costs even if you interrupt the command before it is fully executed. You can run `azd down` or delete the resources manually to avoid unnecessary spending.
