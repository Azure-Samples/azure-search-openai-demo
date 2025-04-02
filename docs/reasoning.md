# RAG chat: Using reasoning models

This repository includes an optional feature that uses reasoning models to generate responses based on retrieved content. These models spend more time processing and understanding the user's request.

## Using the feature

### Supported Models

* o3-mini
* o1

### Prerequisites

* The ability to deploy a reasoning model in the [supported regions](https://learn.microsoft.com/azure/ai-services/openai/concepts/models#standard-deployment-model-availability). If you're not sure, try to create a o3-mini deployment from your Azure OpenAI deployments page.

### Deployment

1. **Enable reasoning:**

   Set the environment variables for your Azure OpenAI GPT deployments to your reasoning model

   ```shell
   azd env set AZURE_OPENAI_CHATGPT_MODEL o3-mini
   azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT o3-mini
   ```

2. **(Optional) Set default reasoning effort**

   You can configure how much effort the reasoning model spends on processing and understanding the user's request. Valid options are `low`, `medium`, and `high`. Reasoning effort defaults to `medium` if not set.

   Set the environment variable for reasoning effort

   ```shell
   azd env set AZURE_OPENAI_REASONING_EFFORT medium
   ```

3. **Clean old deployments (optional):**
   Run `azd down --purge` for a fresh setup.

4. **Start the application:**
   Execute `azd up` to build, provision, deploy, and initiate document preparation.

5. **Try out the feature:**
    ![Reasoning configuration screenshot](./images/reasoning.png)
    ![Thought process token usage](./images/token-usage.png)
   * Access the developer options in the web app and change "Reasoning Effort".
   * Token usage is visible in the thought process tab

