export const enum Approaches {
    RetrieveThenRead = "rtr",
    ReadRetrieveRead = "rrr",
    ReadDecomposeAsk = "rda",
    ChatConversation = "chatconversation"
}

export type AskRequestOverrides = {
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

export type AskRequest = {
    question: string;
    approach: Approaches;
    overrides?: AskRequestOverrides;
};

export type AskResponse = {
    answer: string;
    thoughts: string | null;
    data_points: string[];
    conversation_id: string;
    error?: string;
};

export type ChatTurn = {
    user: string;
    bot?: string;
};

export type ChatRequest = {
    history: ChatTurn[];
    approach: Approaches;
    overrides?: AskRequestOverrides;
    conversation_id?: string;
};

//BDL: for interacting with conversations
export type ChatCompletionsFormat = [
    {
        role: "system" | "user" | "assistant";
        content: string;
    }
];
export type BotFrontendFormat = [{ user: string; bot: string }];

export type ConversationRequest = {
    baseroute: "/conversation";
    route: "/add" | "/read" | "/delete" | "/update" | "/list";
    conversation_id?: string | null;
    approach?: Approaches;
};

export type ConversationResponse = {
    conversation_id: string;
    messages: BotFrontendFormat;
    error?: string;
};

export type ConversationListResponse = {
    _attachments: string;
    _etag: string;
    _rid: string;
    _self: string;
    _ts: Number;
    createdAt: string;
    id: string;
    summary: string;
    title: string;
    type: "conversation";
    updatedAt: string;
    userId: string;
}[];
