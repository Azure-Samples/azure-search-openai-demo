# Deploying with minimal costs

This AI RAG chat application is designed to be easily deployed using the Azure Developer CLI, which provisions the infrastructure according to the Bicep files in the `infra` folder. Those files describe each of the Azure resources needed, and configures their SKU (pricing tier) and other parameters. Many Azure services offer a free tier, but the infrastructure files in this project do *not* default to the free tier as there are often limitations in that tier.

However, if your goal is to minimize costs while prototyping your application, follow the steps below _before_ running `azd up`. Once you've gone through these steps, return to the [deployment steps](../README.md#deploying).

[📺 Live stream: Deploying from a free account](https://www.youtube.com/watch?v=nlIyos0RXHw)

2. Use the free tier of App Service:

    ```shell
    azd env set AZURE_APP_SERVICE_SKU F1
    ```

    Limitation: You are only allowed a certain number of free App Service instances per region. If you have exceeded your limit in a region, you will get an error during the provisioning stage. If that happens, you can run `azd down`, then `azd env new` to create a new environment with a new region.

3. Use the free tier of Azure AI Search:

    ```shell
    azd env set AZURE_SEARCH_SERVICE_SKU free
    ```

    Limitations:
    1. You are only allowed one free search service across all regions.
    If you have one already, either delete that service or follow instructions to
    reuse your [existing search service](../README.md#existing-azure-ai-search-resource).
    2. The free tier does not support semantic ranker, so the app UI will no longer display
    the option to use the semantic ranker. Note that will generally result in [decreased search relevance](https://techcommunity.microsoft.com/t5/ai-azure-ai-services-blog/azure-ai-search-outperforming-vector-search-with-hybrid/ba-p/3929167).
    3. The free tier does not support Managed Identity (keyless API access),
    so the Bicep will use Azure Key Vault to securely store the key instead.

4. Use the free tier of Azure Document Intelligence (used in analyzing files):

    
    ```shell
    azd env set AZURE_DOCUMENTINTELLIGENCE_SKU F0
    ```

    **Limitation for PDF files:**

      The free tier will only scan the first two pages of each PDF.
      In our sample documents, those first two pages are just title pages,
      so you won't be able to get answers from the documents.
      You can either use your own documents that are only 2-pages long,
      or you can use a local Python package for PDF parsing by setting:

      ```shell
      azd env set USE_LOCAL_PDF_PARSER true
      ```

    **Limitation for HTML files:**

      The free tier will only scan the first two pages of each HTML file.
      So, you might not get very accurate answers from the files.
      You can either use your own files that are only 2-pages long,
      or you can use a local Python package for HTML parsing by setting:

      ```shell
      azd env set USE_LOCAL_HTML_PARSER true
      ```

5. Turn off Azure Monitor (Application Insights):

    ```shell
    azd env set AZURE_USE_APPLICATION_INSIGHTS false
    ```

    Application Insights is quite inexpensive already, so turning this off may not be worth the costs saved,
    but it is an option for those who want to minimize costs.

6. Use OpenAI.com instead of Azure OpenAI: This is only a necessary step for Azure free/student accounts, as they do not currently have access to Azure OpenAI.

    ```shell
    azd env set OPENAI_HOST openai
    azd env set OPENAI_ORGANIZATION {Your OpenAI organization}
    azd env set OPENAI_API_KEY {Your OpenAI API key}
    ```

    Both Azure OpenAI and openai.com OpenAI accounts will incur costs, based on tokens used,
    but the costs are fairly low for the amount of sample data (less than $10).

6. Disable vector search:

    ```shell
    azd env set USE_VECTORS false
    ```

    By default, the application computes vector embeddings for documents during the data ingestion phase,
    and then computes a vector embedding for user questions asked in the application.
    Those computations require an embedding model, which incurs costs per tokens used. The costs are fairly low,
    so the benefits of vector search would typically outweigh the costs, but it is possible to disable vector support.
    If you do so, the application will fall back to a keyword search, which is less accurate.

7. Once you've made the desired customizations, follow the steps in [to run `azd up`](../README.md#deploying-from-scratch). We recommend using "eastus" as the region, for availability reasons.

## Reducing costs locally

To save costs for local development, you could use an OpenAI-compatible model.
Follow steps in [local development guide](localdev.md#using-a-local-openai-compatible-api).
