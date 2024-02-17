# Deploying with the Azure Developer CLI

This guide includes advanced topics that are not necessary for a basic deployment. If you are new to the project, please consult the main [README](../README.md#deploying-from-scratch) for steps on deploying the project.

[📺 Watch: Deployment of your chat app](https://www.youtube.com/watch?v=mDFZdmn7nhk)

* [How does `azd up` work?](#how-does-azd-up-work)
* [Configuring continuous deployment](#configuring-continuous-deployment)
  * [GitHub actions](#github-actions)
  * [Azure DevOps](#azure-devops)

## How does `azd up` work?

The `azd up` command comes from the [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview), and takes care of both provisioning the Azure resources and deploying code to the selected Azure hosts.

The `azd up` command uses the `azure.yaml` file combined with the infrastructure-as-code `.bicep` files in the `infra/` folder. The `azure.yaml` file for this project declares several "hooks" for the prepackage step and postprovision steps. The `up` command first runs the `prepackage` hook which installs Node dependencies and builds the React.JS-based JavaScript files. It then packages all the code (both frontend and backend) into a zip file which it will deploy later.

Next, it provisions the resources based on `main.bicep` and `main.parameters.json`. At that point, since there is no default value for the OpenAI resource location, it asks you to pick a location from a short list of available regions. Then it will send requests to Azure to provision all the required resources. With everything provisioned, it runs the `postprovision` hook to process the local data and add it to an Azure AI Search index.

Finally, it looks at `azure.yaml` to determine the Azure host (appservice, in this case) and uploads the zip to Azure App Service. The `azd up` command is now complete, but it may take another 5-10 minutes for the App Service app to be fully available and working, especially for the initial deploy.

Related commands are `azd provision` for just provisioning (if infra files change) and `azd deploy` for just deploying updated app code.

## Configuring continuous deployment

This repository includes both a GitHub Actions workflow and an Azure DevOps pipeline for continuous deployment with every push to `main`. The GitHub Actions workflow is the default, but you can switch to Azure DevOps if you prefer.

More details are available in [Learn.com: Configure a pipeline and push updates](https://learn.microsoft.com/azure/developer/azure-developer-cli/configure-devops-pipeline?tabs=GitHub)

### GitHub actions

After you have deployed the app once with `azd up`, you can enable continuous deployment with GitHub Actions.

Run this command to set up a Service Principal account for CI deployment and to store your `azd` environment variables in GitHub Actions secrets:

```shell
azd pipeline config
```

You can trigger the "Deploy" workflow manually from your GitHub actions, or wait for the next push to main.

If you change your `azd` environment variables at any time (via `azd env set` or as a result of provisioning), re-run that command in order to update the GitHub Actions secrets.

### Azure DevOps

After you have deployed the app once with `azd up`, you can enable continuous deployment with Azure DevOps.

Run this command to set up a Service Principal account for CI deployment and to store your `azd` environment variables in GitHub Actions secrets:

```shell
azd pipeline config --provider azdo
```

If you change your `azd` environment variables at any time (via `azd env set` or as a result of provisioning), re-run that command in order to update the GitHub Actions secrets.
