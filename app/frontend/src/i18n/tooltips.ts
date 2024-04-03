// Keep values less than 20 words.
// Don't add links to the tooltips.
export const toolTipText = {
    promptTemplate: "Allows user to override the chatbot's prompt.",
    temperature: "Controls how creative the generated responses are.",
    searchScore: "Controls the minumum relevancy score between the AI search results and the question.",
    rerankerScore:
        "Controls the minumum relevancy score between the AI search results and the question in a second step to improve the accuracy and relevancy of the response.",
    retrieveNumber: "Number of results affecting final answer",
    excludeCategory: "Example categories include ...",
    useSemanticReranker:
        "Add a second step that evalutes the minumum relevancy score between the AI search responses and the question then promote the most semantically relevant results.",
    useQueryContextSummaries:
        "Can improve the relevance and accuracy of search results by providing a more concise and focused summary of the most relevant information related to the query or context.",
    suggestFollowupQuestions: "Provide follow-up questions to continue conversation.",
    useGPT4: "Controls whether to use GPT 4 Vision in responding or not to enable infromation extraction from images.",
    retrievalMode:
        "The retrieval mode choices determine how the chatbot retrieves and ranks responses based on semantic similarity to the user's query. `Vectors + Text, aka (Hybrid)` uses a combination of vector embeddings and text matching, `Vectors` uses only vector embeddings, and `Text` uses only text matching.",
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
