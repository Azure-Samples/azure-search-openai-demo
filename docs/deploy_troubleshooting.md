# RAG chat: Troubleshooting deployment

If you are experiencing an error when deploying the RAG chat solution using the [deployment steps](../README.md#deploying), this guide will help you troubleshoot common issues.

1. You're attempting to create resources in regions not enabled for Azure OpenAI (e.g. East US 2 instead of East US), or where the model you're trying to use isn't enabled. See [this matrix of model availability](https://aka.ms/oai/models).

> 💡 **Note (April 1st 2025): Regions available for both services**: australiaeast, brazilsouth, eastus, eastus2, francecentral, germanywestcentral, japaneast, koreacentral, northcentralus, norwayeast, southafricanorth, southcentralus, swedencentral, switzerlandnorth, uaenorth, uksouth, westeurope, westus, westus3


1. You've exceeded a quota, most often number of resources per region. See [this article on quotas and limits](https://aka.ms/oai/quotas).

1. You're getting "same resource name not allowed" conflicts. That's likely because you've run the sample multiple times and deleted the resources you've been creating each time, but are forgetting to purge them. Azure keeps resources for 48 hours unless you purge from soft delete. See [this article on purging resources](https://learn.microsoft.com/azure/cognitive-services/manage-resources?tabs=azure-portal#purge-a-deleted-resource).

1. You see `CERTIFICATE_VERIFY_FAILED` when the `prepdocs.py` script runs. That's typically due to incorrect SSL certificates setup on your machine. Try the suggestions in this [StackOverflow answer](https://stackoverflow.com/questions/35569042/ssl-certificate-verify-failed-with-python3/43855394#43855394).

1. After running `azd up` and visiting the website, you see a '404 Not Found' in the browser. Wait 10 minutes and try again, as it might be still starting up. Then try running `azd deploy` and wait again. If you still encounter errors with the deployed app and are deploying to App Service, consult the [guide on debugging App Service deployments](/docs/appservice.md). Please file an issue if the logs don't help you resolve the error.

1. How to resolve other potential error messages:
- [Quota and resources available: InsufficientQuota](./deploy_fix.md#error-message-quota-and-resources-available-insufficientquota).
- [The subscription ID cannot have more than 2 container app environments](./deploy_fix.md#maxnumberofglobalenviromentsinsubexceeded-the-subscription-id-cannot-have-more-than-2-container-app-environments)
- [Cargo is not installed](./deploy_fix.md#cargo-the-rust-package-manager-is-not-installed-or-is-not-on-path)