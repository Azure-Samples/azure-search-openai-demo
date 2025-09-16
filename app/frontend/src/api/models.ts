export const enum RetrievalMode {
    Hybrid = "hybrid",
    Vectors = "vectors",
    Text = "text"
}

export type ChatAppRequestOverrides = {
    retrieval_mode?: RetrievalMode;
    semantic_ranker?: boolean;
    semantic_captions?: boolean;
    query_rewriting?: boolean;
    reasoning_effort?: string;
    include_category?: string;
    exclude_category?: string;
    seed?: number;
    top?: number;
    results_merge_strategy?: string;
    temperature?: number;
    minimum_search_score?: number;
    minimum_reranker_score?: number;
    prompt_template?: string;
    prompt_template_prefix?: string;
    prompt_template_suffix?: string;
    suggest_followup_questions?: boolean;
    use_oid_security_filter?: boolean;
    use_groups_security_filter?: boolean;
    send_text_sources: boolean;
    send_image_sources: boolean;
    search_text_embeddings: boolean;
    search_image_embeddings: boolean;
    language: string;
    use_agentic_retrieval: boolean;
};

export type ResponseMessage = {
    content: string;
    role: string;
};

export type Thoughts = {
    title: string;
    description: any; // It can be any output from the api
    props?: { [key: string]: any };
};

export type DataPoints = {
    text: string[];
    images: string[];
    citations: string[];
};

export type ResponseContext = {
    data_points: DataPoints;
    followup_questions: string[] | null;
    thoughts: Thoughts[];
};

export type ChatAppResponseOrError = {
    message: ResponseMessage;
    delta: ResponseMessage;
    context: ResponseContext;
    session_state: any;
    error?: string;
};

export type ChatAppResponse = {
    message: ResponseMessage;
    delta: ResponseMessage;
    context: ResponseContext;
    session_state: any;
};

export type ChatAppRequestContext = {
    overrides?: ChatAppRequestOverrides;
};

export type ChatAppRequest = {
    messages: ResponseMessage[];
    context?: ChatAppRequestContext;
    session_state: any;
};

export type Config = {
    defaultReasoningEffort: string;
    showMultimodalOptions: boolean;
    showSemanticRankerOption: boolean;
    showQueryRewritingOption: boolean;
    showReasoningEffortOption: boolean;
    streamingEnabled: boolean;
    showVectorOption: boolean;
    showUserUpload: boolean;
    showLanguagePicker: boolean;
    showSpeechInput: boolean;
    showSpeechOutputBrowser: boolean;
    showSpeechOutputAzure: boolean;
    showChatHistoryBrowser: boolean;
    showChatHistoryCosmos: boolean;
    showAgenticRetrievalOption: boolean;
    ragSearchTextEmbeddings: boolean;
    ragSearchImageEmbeddings: boolean;
    ragSendTextSources: boolean;
    ragSendImageSources: boolean;
};

export type SimpleAPIResponse = {
    message?: string;
};

export interface SpeechConfig {
    speechUrls: (string | null)[];
    setSpeechUrls: (urls: (string | null)[]) => void;
    audio: HTMLAudioElement;
    isPlaying: boolean;
    setIsPlaying: (isPlaying: boolean) => void;
}

export type HistoryListApiResponse = {
    sessions: {
        id: string;
        entra_oid: string;
        title: string;
        timestamp: number;
    }[];
    continuation_token?: string;
};

export type HistoryApiResponse = {
    id: string;
    entra_oid: string;
    answers: any;
};
