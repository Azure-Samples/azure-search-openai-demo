export type QueryPlanStep = {
    id: number | string;
    type: string;
    elapsed_ms?: number;
    knowledge_source_name?: string;
    search_index_arguments?: {
        search?: string;
        search_fields?: string[];
        semantic_configuration_name?: string;
        source_data_fields?: { name?: string }[];
    };
    web_arguments?: {
        search?: string;
    };
    remote_share_point_arguments?: {
        search?: string;
    };
    query_time?: string;
    count?: number;
    input_tokens?: number;
    output_tokens?: number;
    reasoning_tokens?: number;
    retrieval_reasoning_effort?: {
        kind?: string;
    };
    [key: string]: unknown;
};

const STEP_LABELS: Record<string, string> = {
    modelQueryPlanning: "Query planning",
    searchIndex: "Search index",
    web: "Web search",
    remoteSharePoint: "Search SharePoint",
    agenticReasoning: "Agentic reasoning",
    modelAnswerSynthesis: "Answer synthesis"
};

export const getStepLabel = (step: QueryPlanStep) => STEP_LABELS[step.type] ?? step.type;
