export const enum ChatApproaches {
    ReadRetrieveRead = "rrr",
    ReadRetrieveRead_LC = "rrr_lc",
    ReadRetrieveRead_SK = "rrr_sk"
}

export type AskResponse = {
    answer: string;
    citations: Citation[];
    error?: string;
};

export type Citation = {
    content: string;
    id: string;
    title: string | null;
    filepath: string | null;
    url: string | null;
    metadata: string | null;
    chunk_id: string | null;
    reindex_id: string | null;
};

export type ToolMessageContent = {
    citations: Citation[];
    intent: string;
};

export type ChatMessage = {
    role: string;
    content: string;
    end_turn?: boolean;
};

export enum ChatCompletionType {
    ChatCompletion = "chat.completion",
    ChatCompletionChunk = "chat.completion.chunk"
}

export type ChatResponseChoice = {
    messages: ChatMessage[];
};

export type ChatResponseAOAI = {
    id: string;
    model: string;
    created: number;
    object: ChatCompletionType;
    choices: ChatResponseChoice[];
    error?: any;
};

export type ConversationRequest = {
    messages: ChatMessage[];
};

export type UserInfo = {
    access_token: string;
    expires_on: string;
    id_token: string;
    provider_name: string;
    user_claims: any[];
    user_id: string;
};

//////////////

export type AskRequestOverrides = {
    semanticRanker?: boolean;
    semanticCaptions?: boolean;
    excludeCategory?: string;
    top?: number;
    temperature?: number;
    promptTemplate?: string;
    promptTemplatePrefix?: string;
    promptTemplateSuffix?: string;
};

export type ChatResponse = {
    answer: string;
    citations: string[];
    thoughts: string | null;
    data_points: string[];
    error?: string;
};

export type ChatTurn = {
    user: string;
    bot?: string;
};

export type ChatRequest = {
    history: ChatTurn[];
    approach: ChatApproaches;
    overrides?: AskRequestOverrides;
};
