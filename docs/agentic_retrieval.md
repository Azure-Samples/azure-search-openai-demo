# RAG chat: Using agentic retrieval

This repository includes an optional feature that uses agentic retrieval to find the most relevant content given a user's conversation history.

## Using the feature

### Supported Models

See the agentic retrieval documentation.

### Prerequisites

* A deployment of any of the supported agentic retrieval models in the [supported regions](https://learn.microsoft.com/azure/ai-services/openai/concepts/models#standard-deployment-model-availability). If you're not sure, try to create a gpt-4.1-mini deployment from your Azure OpenAI deployments page.

### Deployment

1. **Enable agentic retrieval:**

   Set the environment variables for your Azure OpenAI GPT deployments to your reasoning model

   ```shell
   azd env set USE_AGENTIC_RETRIEVAL true
   ```

2. **(Optional) Set the agentic retrieval model**

   You can configure which model agentic retrieval uses. By default, gpt-4.1-mini is used.

   To change the model, set the following environment variables appropriately:

   ```shell
   azd env set AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT searchagent
   azd env set AZURE_OPENAI_SEARCHAGENT_MODEL gpt-4.1-mini
   azd env set AZURE_OPENAI_SEARCHAGENT_MODEL_VERSION 2025-04-14
   ```

3. **(Optional) Enable extra field hydration**

   By default, agentic retrieval only returns fields included in the semantic configuration.

   You can enable this optional feature below, to include all fields from the search index in the result.
   ⚠️ This feature is currently only compatible with indexes set up with integrated vectorization,
   or indexes that otherwise have an "id" field marked as filterable.

   ```shell
   azd env set ENABLE_AGENTIC_RETRIEVAL_SOURCE_DATA true
   ```

4. **Update the infrastructure and application:**

   Execute `azd up` to provision the infrastructure changes (only the new model, if you ran `up` previously) and deploy the application code with the updated environment variables.

5. **Try out the feature:**

   Open the web app and start a new chat. Agentic retrieval will be used to find all sources.

6. **Review the query plan**

   Agentic retrieval use additional billed tokens behind the scenes for the planning process.
   To see the token usage, select the lightbulb icon on a chat answer. This will open the "Thought process" tab, which shows the amount of tokens used by and the queries produced by the planning process

   ![Thought process token usage](./images/query-plan.png)
