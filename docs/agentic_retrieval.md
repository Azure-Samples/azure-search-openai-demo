# RAG chat: Using agentic retrieval

This repository includes an optional feature that uses [agentic retrieval from Azure AI Search](https://learn.microsoft.com/azure/search/search-agentic-retrieval-concept) to find the most relevant content given a user's conversation history. The agentic retrieval feature uses a LLM to analyze the conversation and generate multiple search queries to find relevant content. This can improve the quality of the responses, especially for complex or multi-faceted questions.

## Deployment

1. **Enable agentic retrieval:**

   Set the azd environment variable to enable the agentic retrieval feature:

   ```shell
   azd env set USE_AGENTIC_RETRIEVAL true
   ```

2. **(Optional) Customize the agentic retrieval model**

   You can configure which model agentic retrieval uses. By default, gpt-4.1-mini is used.

   To change the model, set the following environment variables appropriately:

   ```shell
   azd env set AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT searchagent
   azd env set AZURE_OPENAI_SEARCHAGENT_MODEL gpt-4.1-mini
   azd env set AZURE_OPENAI_SEARCHAGENT_MODEL_VERSION 2025-04-14
   ```

   You can only change it to one of the [supported models](https://learn.microsoft.com/azure/search/search-agentic-retrieval-how-to-create#supported-models).

3. **Update the infrastructure and application:**

   Execute `azd up` to provision the infrastructure changes (only the new model, if you ran `up` previously) and deploy the application code with the updated environment variables. The post-provision script will configure Azure AI Search with a Knowledge agent pointing at the search index.

4. **Try out the feature:**

   Open the web app and start a new chat. Agentic retrieval will be used to find all sources.

5. **Review the query plan**

   Agentic retrieval uses additional billed tokens behind the scenes for the planning process.
   To see the token usage, select the lightbulb icon on a chat answer. This will open the "Thought process" tab, which shows the amount of tokens used by and the queries produced by the planning process

   ![Thought process token usage](./images/query-plan.png)
