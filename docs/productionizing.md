# Productionizing the Chat App

This sample is designed to be a starting point for your own production application,
but you should do a thorough review of the security and performance before deploying
to production. Here are some things to consider:

* [Azure resource configuration](#azure-resource-configuration)
* [Additional security measures](#additional-security-measures)
* [Load testing](#load-testing)
* [Evaluation](#evaluation)

## Azure resource configuration

### OpenAI Capacity

The default TPM (tokens per minute) is set to 30K. That is equivalent
to approximately 30 conversations per minute (assuming 1K per user message/response).
You can increase the capacity by changing the `chatGptDeploymentCapacity` and `embeddingDeploymentCapacity`
parameters in `infra/main.bicep` to your account's maximum capacity.
You can also view the Quotas tab in [Azure OpenAI studio](https://oai.azure.com/)
to understand how much capacity you have.

If the maximum TPM isn't enough for your expected load, you have a few options:

* Use a backoff mechanism to retry the request. This is helpful if you're running into a short-term quota due to bursts of activity but aren't over long-term quota. The [tenacity](https://tenacity.readthedocs.io/en/latest/) library is a good option for this, and this [pull request](https://github.com/Azure-Samples/azure-search-openai-demo/pull/500) shows how to apply it to this app.

* If you are consistently going over the TPM, then consider implementing a load balancer between OpenAI instances. Most developers implement that using Azure API Management or container-based load balancers. A native Python approach that integrates with the OpenAI Python API Library is also possible. For integration instructions with this sample, please check:
  * [Scale Azure OpenAI for Python with Azure API Management](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-scaling-with-azure-api-management)
  * [Scale Azure OpenAI for Python chat using RAG with Azure Container Apps](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-scaling-with-azure-container-apps)
  * [Pull request: Scale Azure OpenAI for Python with the Python openai-priority-loadbalancer](https://github.com/Azure-Samples/azure-search-openai-demo/pull/1626)

### Azure Storage

The default storage account uses the `Standard_LRS` SKU.
To improve your resiliency, we recommend using `Standard_ZRS` for production deployments,
which you can specify using the `sku` property under the `storage` module in `infra/main.bicep`.

### Azure AI Search

The default search service uses the "Basic" SKU
with the free semantic ranker option, which gives you 1000 free queries a month.
After 1000 queries, you will get an error message about exceeding the semantic ranker free capacity.

* Assuming your app will experience more than 1000 questions per month,
  you should upgrade the semantic ranker SKU from "free" to "standard" SKU:

  ```shell
  azd env set AZURE_SEARCH_SEMANTIC_RANKER standard
  ```

  Or disable semantic search entirely:

  ```shell
  azd env set AZURE_SEARCH_SEMANTIC_RANKER disabled
  ```

* The search service can handle fairly large indexes, but it does have per-SKU limits on storage sizes, maximum vector dimensions, etc. You may want to upgrade the SKU to either a Standard or Storage Optimized SKU, depending on your expected load.
However, you [cannot change the SKU](https://learn.microsoft.com/azure/search/search-sku-tier#tier-upgrade-or-downgrade) of an existing search service, so you will need to re-index the data or manually copy it over.
You can change the SKU by setting the `AZURE_SEARCH_SERVICE_SKU` azd environment variable to [an allowed SKU](https://learn.microsoft.com/azure/templates/microsoft.search/searchservices?pivots=deployment-language-bicep#sku).

  ```shell
  azd env set AZURE_SEARCH_SERVICE_SKU standard
  ```

  See the [Azure AI Search service limits documentation](https://learn.microsoft.com/azure/search/search-limits-quotas-capacity) for more details.

* If you see errors about search service capacity being exceeded, you may find it helpful to increase
the number of replicas by changing `replicaCount` in `infra/core/search/search-services.bicep`
or manually scaling it from the Azure Portal.

### Azure App Service

The default app service plan uses the `Basic` SKU with 1 CPU core and 1.75 GB RAM.
We recommend using a Premium level SKU, starting with 1 CPU core.
You can use auto-scaling rules or scheduled scaling rules,
and scale up the maximum/minimum based on load.

## Additional security measures

* **Authentication**: By default, the deployed app is publicly accessible.
  We recommend restricting access to authenticated users.
  See [Enabling authentication](./deploy_features.md#enabling-authentication) to learn how to enable authentication.
* **Networking**: We recommend [deploying inside a Virtual Network](./deploy_private.md). If the app is only for
  internal enterprise use, use a private DNS zone. Also consider using Azure API Management (APIM)
  for firewalls and other forms of protection.
  For more details, read [Azure OpenAI Landing Zone reference architecture](https://techcommunity.microsoft.com/t5/azure-architecture-blog/azure-openai-landing-zone-reference-architecture/ba-p/3882102).

## Load testing

We recommend running a loadtest for your expected number of users.
You can use the [locust tool](https://docs.locust.io/) with the `locustfile.py` in this sample
or set up a loadtest with Azure Load Testing.

To use locust, first install the dev requirements that includes locust:

```shell
python -m pip install -r requirements-dev.txt
```

Or manually install locust:

```shell
python -m pip install locust
```

Then run the locust command, specifying the name of the User class to use from `locustfile.py`. We've provided a `ChatUser` class that simulates a user asking questions and receiving answers, as well as a `ChatVisionUser` to simulate a user asking questions with the [GPT-4 vision mode enabled](/docs/gpt4v.md).

```shell
locust ChatUser
```

Open the locust UI at [http://localhost:8089/](http://localhost:8089/), the URI displayed in the terminal.

Start a new test with the URI of your website, e.g. `https://my-chat-app.azurewebsites.net`.
Do *not* end the URI with a slash. You can start by pointing at your localhost if you're concerned
more about load on OpenAI/AI Search than the host platform.

For the number of users and spawn rate, we recommend starting with 20 users and 1 users/second.
From there, you can keep increasing the number of users to simulate your expected load.

Here's an example loadtest for 50 users and a spawn rate of 1 per second:

![Screenshot of Locust charts showing 5 requests per second](images/screenshot_locust.png)

After each test, check the local or App Service logs to see if there are any errors.

## Evaluation

Before you make your chat app available to users, you'll want to rigorously evaluate the answer quality. You can use tools in [the AI RAG Chat evaluator](https://github.com/Azure-Samples/ai-rag-chat-evaluator) repository to run evaluations, review results, and compare answers across runs.
