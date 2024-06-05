// Keep values less than 20 words.
// Don't add links to the tooltips.
export const toolTipText = {
    promptTemplate:
        "Overrides the prompt used to generate the answer based on the question and search results. To append to existing prompt instead of replace whole prompt, start your prompt with '>>>'.",
    temperature:
        "Sets the temperature of the request to the LLM that generates the answer. Higher temperatures result in more creative responses, but they may be less grounded.",
    searchScore:
        "Sets a minimum score for search results coming back from Azure AI search. The score range depends on whether you're using hybrid (default), vectors only, or text only.",
    rerankerScore:
        "Sets a minimum score for search results coming back from the semantic reranker. The score always ranges between 1-4. The higher the score, the more semantically relevant the result is to the question.",
    retrieveNumber:
        "Sets the number of search results to retrieve from Azure AI search. More results may increase the likelihood of finding the correct answer, but may lead to the model getting 'lost in the middle'.",
    excludeCategory: "Specifies a category to exclude from the search results. There are no categories used in the default data set.",
    useSemanticReranker: "Enables the Azure AI Search semantic ranker, a model that re-ranks search results based on semantic similarity to the user's query.",
    useSemanticCaptions:
        "Sends semantic captions to the LLM instead of the full search result. A semantic caption is extracted from a search result during the process of semantic ranking.",
    suggestFollowupQuestions: "Asks the LLM to suggest follow-up questions based on the user's query.",
    useGPT4Vision: "Uses GPT-4-Turbo with Vision to generate responses based on images and text from the index.",
    vectorFields:
        "Specifies which embedding fields in the Azure AI Search Index will be searched, both the 'Images and text' embeddings, 'Images' only, or 'Text' only.",
    gpt4VisionInputs:
        "Sets what will be send to the vision model. 'Images and text' sends both images and text to the model, 'Images' sends only images, and 'Text' sends only text.",
    retrievalMode:
        "Sets the retrieval mode for the Azure AI Search query. `Vectors + Text (Hybrid)` uses a combination of vector search and full text search, `Vectors` uses only vector search, and `Text` uses only full text search. Hybrid is generally optimal.",
    streamChat: "Continuously streams the response to the chat UI as it is generated.",
    useOidSecurityFilter: "Filter search results based on the authenticated user's OID.",
    useGroupsSecurityFilter: "Filter search results based on the authenticated user's groups."
};
