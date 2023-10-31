# Customizing the Chat App

This guide provides more details for customizing the Chat App.

## Using your own data

The Chat App is designed to work with any PDF documents. The sample data is provided to help you get started quickly, but you can easily replace it with your own data. You'll want to first remove all the existing data, then add your own. See the [data ingestion guide](data_ingestion.md) for more details.

## Customizing the UI

The frontend is built using [React](https://reactjs.org/) and [Fluent UI components](https://react.fluentui.dev/). The frontend components are stored in the `app/frontend/src` folder. The typical components you'll want to customize are:

- `app/frontend/index.html`: To change the page title
- `app/frontend/src/pages/layout/Layout.tsx`: To change the header text and logo
- `app/frontend/src/pages/chat/Chat.tsx`: To change the large heading
- `app/frontend/src/components/Example/ExampleList.tsx`: To change the example questions

## Customizing the backend

The backend is built using [Quart](https://quart.palletsprojects.com/), a Python framework for asynchronous web applications. The backend code is stored in the `app/backend` folder.

### Chat/Ask approaches

Typically, the primary backend code you'll want to customize is the `app/backend/approaches` folder, which contains the classes powering the Chat and Ask tabs. Each class uses a different RAG (Retrieval Augmented Generation) approach, which include system messages that should be changed to match your data

#### Chat approach

The chat tab uses the approach programmed in [chatreadretrieveread.py](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/chatreadretrieveread.py).

1. It uses the ChatGPT API to turn the user question into a good search query.
2. It queries Azure Cognitive Search for search results for that query (optionally using the vector embeddings for that query).
3. It then combines the search results and original user question, and asks ChatGPT API to answer the question based on the sources. It includes the last 4K of message history as well (or however many tokens are allowed by the deployed model).

The `system_message_chat_conversation` variable is currently tailored to the sample data since it starts with "Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook." Change that to match your data.

### Ask approach

The ask tab uses the approach programmed in [retrievethenread.py](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/retrievethenread.py).

1. It queries Azure Cognitive Search for search results for the user question (optionally using the vector embeddings for that question).
2. It then combines the search results and user question, and asks ChatGPT API to answer the question based on the sources.

The `system_chat_template` variable is currently tailored to the sample data since it starts with "You are an intelligent assistant helping Contoso Inc employees with their healthcare plan questions and employee handbook questions." Change that to match your data.

## Improving answer quality

Once you are running the chat app on your own data and with your own tailored system prompt,
the next step is to test the app with questions and note the quality of the answers.
If you notice any answers that aren't as good as you'd like, here's a process for improving them.

### Identify the problem point

The first step is to identify where the problem is occurring. For example, if using the Chat tab, the problem could be:

1. ChatGPT is not generating a good search query based on the user question
2. Azure Cognitive Search is not returning good search results for the query
3. ChatGPT is not generating a good answer based on the search results and user question

You can look at the "Thought process" tab in the chat app to see each of those steps,
and determine which one is the problem.

#### Improving ChatGPT results

If the problem is with ChatGPT (steps 1 or 3 above), you can try changing the relevant prompt.

Once you've changed the prompt, make sure you ask the same question multiple times to see if the overall quality has improved. ChatGPT can yield different results every time, even for a temperature of 0.0, but especially for a higher temperature than that (like our default of 0.7 for step 3).

You can also try changing the ChatGPT parameters, like temperature, to see if that improves results for your domain.

#### Improving Azure Cognitive Search results

If the problem is with Azure Cognitive Search (step 2 above), the first step is to check what search parameters you're using. Generally, the best results are found with hybrid search (text + vectors) plus the additional semantic re-ranking step, and that's what we've enabled by default. There may be some domains where that combination isn't optimal, however.

##### Configuring parameters in the app

You can change many of the search parameters in the "Developer settings" in the frontend and see if results improve for your queries. The most relevant options:

![Screenshot of search options in developer settings](search_options.png)

#### Configuring parameters in the Azure Portal

You may find it easier to experiment with search options with the index explorer in the Azure Portal.
Open up the Azure Cognitive Search resource, select the Indexes tab, and select the index there.

Then use the JSON view of the search explorer, and make sure you specify the same options you're using in the app. For example, this query represents a search with semantic ranker configured:

```json
{
  "search": "eye exams",
  "queryType": "semantic",
  "semanticConfiguration": "default",
  "queryLanguage": "en-us",
  "speller": "lexicon",
  "top": 3
}
```

You can also use the `highlight` parameter to see what text is being matched in the `content` field in the search results.

```json
{
    "search": "eye exams",
    "highlight": "content"
    ...
}
```

![Screenshot of search explorer with highlighted results](../images/highlighting.png)

The search explorer works well for testing text, but is harder to use with vectors, since you'd also need to compute the vector embedding and send it in. It is probably easier to use the app frontend for testing vectors/hybrid search.
