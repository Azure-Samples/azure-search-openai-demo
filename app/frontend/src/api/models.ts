export const enum Approaches {
    RetrieveThenRead = "rtr",
    ReadRetrieveRead = "rrr",
    ReadDecomposeAsk = "rda"
}

export const enum RetrievalMode {
    Hybrid = "hybrid",
    Vectors = "vectors",
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
    useOidSecurityFilter?: boolean;
    useGroupsSecurityFilter?: boolean;
};

export type AskRequest = {
    question: string;
    approach: Approaches;
    overrides?: AskRequestOverrides;
    idToken?: string;
};

export type ResponseMessage = {
    content: string;
    role: string;
}

export type ResponseExtraArgs = {
    thoughts: string | null;
    data_points: string[];
}

export type ResponseChoice = {
    index: number;
    message: ResponseMessage;
    extra_args: ResponseExtraArgs;
};

export type AskResponse = {
    choices: ResponseChoice[];
    object: string;
    error?: string; // TODO: This isnt in spec, is it from backend? Can just use HTTP?
};

export type ChatTurn = {
    user: string;
    bot?: string;
};

export type ChatRequest = {
    history: ChatTurn[];
    approach: Approaches;
    overrides?: AskRequestOverrides;
    idToken?: string;
    shouldStream?: boolean;
};
