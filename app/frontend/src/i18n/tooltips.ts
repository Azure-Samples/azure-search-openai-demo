// Keep values less than 20 words.
// Don't add links to the tooltips.
export const toolTipText = {
    approaches: "Retrieve first uses Azure Search. Read first uses LangChain.",
    promptTemplate: "Allows user to override the chatbot's prompt.",
    promptTemplatePrefix: "Allows user to provide a prefix to the chatbot's prompt. For example, `Answer the following question as if I were in high school.`",
    promptTemplateSuffix: "Allows user to provide a suffix to the chatbot's prompt. For example, `Return the first 50 words.`",
    retrieveNumber: "Number of results affecting final answer",
    excludeCategory: "Example categories include ...",
    useSemanticRanker: "Semantic ranker is a machine learning model to improve the relevance and accuracy of search results.",
    useQueryContextSummaries:
        "Can improve the relevance and accuracy of search results by providing a more concise and focused summary of the most relevant information related to the query or context.",
    suggestFollowupQuestions: "Provide follow-up questions to continue conversation.",
    retrievalMode:
        "The retrieval mode choices determine how the chatbot retrieves and ranks responses based on semantic similarity to the user's query. `Vectors + Text (Hybrid)` uses a combination of vector embeddings and text matching, `Vectors` uses only vector embeddings, and `Text` uses only text matching.",
    streamChat: "Continuously deliver responses as they are generated or wait until all responses are generated before delivering them."
};

// beak: triangle color
// beakCurtain: outer edge
// calloutMain: content center
// No style to control text color
export const toolTipTextCalloutProps = {
    styles: {
        beak: { background: "#D3D3D3" },
        beakCurtain: { background: "#D3D3D3" },
        calloutMain: { background: "#D3D3D3" }
    }
};
