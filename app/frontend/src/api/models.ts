export const enum ChatApproaches {
    ReadRetrieveRead = "rrr",
    ReadRetrieveRead_LC = "rrr_lc",
    ReadRetrieveRead_SK = "rrr_sk"
}

export const enum RetrievalMode {
    Text = "text"
}

export type AskRequestOverrides = {
    retrievalMode?: RetrievalMode;
    semanticRanker?: boolean;
    semanticCaptions?: boolean;
    excludeCategory?: string;
    top?: number;
    temperature?: number;
    promptTemplate?: string;
    promptTemplatePrefix?: string;
    promptTemplateSuffix?: string;
    suggestFollowupQuestions?: boolean;
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
