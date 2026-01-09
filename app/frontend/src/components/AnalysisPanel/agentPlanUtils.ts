export type QueryPlanStep = {
    id: number | string;
    type: string;
    label?: string;
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

export const activityTypeLabels: Record<string, string> = {
    modelQueryPlanning: "Query planning",
    searchIndex: "Index search",
    web: "Web search",
    remoteSharePoint: "SharePoint search",
    agenticReasoning: "Agentic reasoning",
    modelAnswerSynthesis: "Answer synthesis"
};

export function getStepLabel(step: QueryPlanStep): string {
    return step.label || activityTypeLabels[step.type] || step.type;
}
