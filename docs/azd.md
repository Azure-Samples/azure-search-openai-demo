# Deploying with the Azure Developer CLI

This guide includes advanced topics that are not necessary for a basic deployment. If you are new to the project, please consult the main [README](../README.md#deploying-from-scratch) for steps on deploying the project.

## How does `azd up` work?

The `azd up` command comes from the [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/overview), and takes care of both provisioning the Azure resources and deploying code to the selected Azure hosts.

The `azd up` command uses the `azure.yaml` file combined with the infrastructure-as-code `.bicep` files in the `infra/` folder. The `azure.yaml` file for this project declares several "hooks" for the prepackage step and postprovision steps. The `up` command first runs the `prepackage` hook which installs Node dependencies and builds the React.JS-based JavaScript files. It then packages all the code (both frontend and backend) into a zip file which it will deploy later.

Next, it provisions the resources based on `main.bicep` and `main.parameters.json`. At that point, since there is no default value for the OpenAI resource location, it asks you to pick a location from a short list of available regions. Then it will send requests to Azure to provision all the required resources. With everything provisioned, it runs the `postprovision` hook to process the local data and add it to an Azure AI Search index.

Finally, it looks at `azure.yaml` to determine the Azure host (appservice, in this case) and uploads the zip to Azure App Service. The `azd up` command is now complete, but it may take another 5-10 minutes for the App Service app to be fully available and working, especially for the initial deploy.

Related commands are `azd provision` for just provisioning (if infra files change) and `azd deploy` for just deploying updated app code.

## Configuring continuous deployment

Please see [PR #1083](https://github.com/Azure-Samples/azure-search-openai-demo/pull/1083) if you are interested in continuous deployment with GitHub Actions or Azure DevOps pipelines. We expect to merge that PR soon.

[📺 Watch: Continuous deployment of your chat app](https://www.youtube.com/watch?v=mDFZdmn7nhk)
