# RAG chat: Troubleshooting deployment

If you are experiencing an error when deploying the RAG chat solution using the [deployment steps](../README.md#deploying), this guide will help you troubleshoot common issues.

1. You're attempting to create resources in regions not enabled for Azure OpenAI (e.g. East US 2 instead of East US), or where the model you're trying to use isn't enabled. See [this matrix of model availability](https://aka.ms/oai/models).

1. You've exceeded a quota, most often number of resources per region. See [this article on quotas and limits](https://aka.ms/oai/quotas).

1. You're getting "same resource name not allowed" conflicts. That's likely because you've run the sample multiple times and deleted the resources you've been creating each time, but are forgetting to purge them. Azure keeps resources for 48 hours unless you purge from soft delete. See [this article on purging resources](https://learn.microsoft.com/azure/cognitive-services/manage-resources?tabs=azure-portal#purge-a-deleted-resource).

1. You see `CERTIFICATE_VERIFY_FAILED` when the `prepdocs.py` script runs. That's typically due to incorrect SSL certificates setup on your machine. Try the suggestions in this [StackOverflow answer](https://stackoverflow.com/questions/35569042/ssl-certificate-verify-failed-with-python3/43855394#43855394).

1. After running `azd up` and visiting the website, you see a '404 Not Found' in the browser. Wait 10 minutes and try again, as it might be still starting up. Then try running `azd deploy` and wait again. If you still encounter errors with the deployed app and are deploying to App Service, consult the [guide on debugging App Service deployments](/docs/appservice.md). Please file an issue if the logs don't help you resolve the error.

# How to resolve other potential error messages:

This section covers common error messages you might encounter when deploying templates locally, along with solutions to resolve them.

- [Quota and resources available: InsufficientQuota](./deploy_troubleshooting.md#error-message-quota-and-resources-available-insufficientquota)
- [The subscription ID cannot have more than 2 container app environments](#maxnumberofglobalenviromentsinsubexceeded-the-subscription-id-cannot-have-more-than-2-container-app-environments)

## Error message: Quota and resources available: InsufficientQuota:
 _This operation require 30 new capacities in quota Tokens Per Minute (thousands) - GPT-35-Turbo, which is bigger than the current available capacity 0. The current quota usage is 30 and the quota limit is 30 for quota Tokens Per Minute (thousands) - GPT-35-Turbo._

Possible solutions: 

1.	Review and adjust the quota: Check if you can increase the quota for Tokens Per Minute (thousands) for your gpt-model in your Azure settings. This might involve requesting a quota increase through the Azure portal.
2.	Contact Azure support: If you can't adjust the quota yourself, reach out to Azure support with the tracking ID for specific assistance with your issue.

## MaxNumberofGlobalEnviromentsInSubExceeded: The subscription ID cannot have more than 2 container app environments.
Possible solutions:

1. Delete Existing Environments: Check if there are any container app environments you no longer need and delete them to free up space.

2. Request a Quota Increase: Request an increase in the limit of container app environments. You can do this through the Azure portal by clicking the help icon (question mark) in the top right corner and creating a support ticket.

3. Review Subscription Configuration: Ensure your subscription is configured correctly and that there are no additional restrictions causing the issue.

4. Use Different Regions: If possible, try creating the environments in different regions to avoid the global limit.