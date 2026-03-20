# RAG chat: Troubleshooting deployment

If you are experiencing an error when deploying the RAG chat solution using the [deployment steps](../README.md#deploying), this guide will help you troubleshoot common issues.

1. You're attempting to create resources in regions not enabled for Azure OpenAI (e.g. East US 2 instead of East US), or where the model you're trying to use isn't enabled. See [this matrix of model availability](https://aka.ms/oai/models).

1. You've exceeded a quota, most often number of resources per region. See [this article on quotas and limits](https://aka.ms/oai/quotas).

1. You're getting "same resource name not allowed" conflicts. That's likely because you've run the sample multiple times and deleted the resources you've been creating each time, but are forgetting to purge them. Azure keeps resources for 48 hours unless you purge from soft delete. See [this article on purging resources](https://learn.microsoft.com/azure/cognitive-services/manage-resources?tabs=azure-portal#purge-a-deleted-resource).

1. You see `CERTIFICATE_VERIFY_FAILED` when the `prepdocs.py` script runs. That's typically due to incorrect SSL certificates setup on your machine. Try the suggestions in this [StackOverflow answer](https://stackoverflow.com/a/43855394).

1. After running `azd up` and visiting the website, you see a '404 Not Found' in the browser. Wait 10 minutes and try again, as it might be still starting up. Then try running `azd deploy` and wait again. If you still encounter errors with the deployed app and are deploying to App Service, consult the [guide on debugging App Service deployments](/docs/appservice.md). Please file an issue if the logs don't help you resolve the error.

1. You see a `RoleAssignmentExists` error (HTTP 409) when re-deploying after switching between local development and CI/CD pipelines (or vice versa). This happens because the role assignment GUID changes when the `principalType` changes between `User` and `ServicePrincipal`. Running `azd up` again should resolve the issue, as the template now generates separate role assignments for each principal type.

1. You see a `PropertyChangeNotAllowed` error referencing Cosmos DB partition keys when re-deploying over an older version of this template. Cosmos DB partition keys are immutable and cannot be changed after container creation. To resolve this, delete the `chat-history-v2` container in Azure Portal or via CLI (`az cosmosdb sql container delete`), then re-deploy. The container will be recreated with the correct MultiHash partition key scheme. Note: existing chat history in that container will be lost.

1. You see a `Conflict` error (HTTP 409) about Cognitive Services resources when re-deploying after a previous `azd down`. Azure soft-deletes Cognitive Services resources for 48 days, blocking re-creation with the same name. The template now includes `restore: true` on all Cognitive Services modules, which automatically restores the soft-deleted resource instead of failing. If you still encounter this issue on an older version of the template, you can manually purge the soft-deleted resource via [the Azure CLI](https://learn.microsoft.com/azure/ai-services/manage-resources?tabs=azure-portal#purge-a-deleted-resource).
