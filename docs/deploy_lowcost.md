## Deploying with minimal costs

This AI RAG chat application is designed to be easily deployed using the Azure Developer CLI, which provisions the infrastructure according to the Bicep files in the `infra` folder. Those files describe each of the Azure resources needed, and configures their SKU (pricing tier) and other parameters. Many Azure services offer a free tier, but the infrastructure files in this project do *not* default to the free tier as there are often limitations in that tier.

However, if your goal is to minimize costs while prototyping your application, you can follow these steps to minimize the costs as much as possible, _before_ deploying the application.

1. Use the free tier of App Service:

    ```shell
    azd env set AZURE_APP_SERVICE_SKU F1
    ```

    Limitation: You are only allowed a certain number of free App Service instances per region. If you have exceeded your limit in a region, you will get an error during the provisioning stage. If that happens, you can run `azd down`, then `azd env new` to create a new environment with a new region.

2. Use the free tier of Azure AI Search:

    ```shell
    azd env set AZURE_SEARCH_SERVICE_SKU free
    ```

    Limitations:
    1. You are only allowed one free search service across all regions.
    If you have one already, either delete that service or follow instructions to
    reuse your [existing search service](../README.md#existing-azure-ai-search-resource).
    2. The free tier does not support semantic ranker, so you will need to disable
    that option in the developer settings. You should change the default of `useSemanticRanker`
    in `Chat.tsx` to `false` instead of `true`.
    3. The free tier does not support Managed Identity (keyless API access),
    so if you enable the free tier, the Bicep will use Azure Key Vault to securely store the key instead.

3. Use the free tier of Azure Document Intelligence (used in analyzing PDFs):

    ```shell
    azd env set AZURE_FORMRECOGNIZER_SKU free
    ```

    Limitation: The free tier will only scan the first two pages of each PDF.
    In our sample documents, those first two pages are just title pages,
    so you won't be able to get answers from the documents.
    You can either use your own documents that are only 2-pages long,
    or you can use a local Python package for PDF parsing by adding the `--localpdfparser`
    argument to the command at the bottom of `prepdocs.sh` or `prepdocs.ps1`.

3. Turn off Azure Monitor (Application Insights):

    ```shell
    azd env set AZURE_USE_APPLICATION_INSIGHTS false
    ```

    Application Insights is quite inexpensive already, so turning this off may not be worth the costs saved,
    but it is an option for those who want to minimize costs.

4. Disable vector search:

    By default, the application computes vector embeddings for documents during the data ingestion phase,
    and then computes a vector embedding for user questions asked in the application.
    Those computations require an embedding model, which incurs costs per tokens used. The costs are fairly low,
    so the benefits of vector search would typically outweigh the costs, but it is possible to disable vector support.

    Modify `prepdocs.sh` or `prepdocs.ps1` to add the `--novectors` argument to the command at the bottom.

    Modify `Chat.tsx` so that `retrievalMode` defaults to `RetrievalMode.Text` instead of `RetrievalMode.HYBRID`.

* Use a local OpenAI-compatible model:

    To save costs for local development, you could use an OpenAI-compatible model.
    Follow steps in [local development guide](localdev.md#using-a-local-openai-compatible-api).
